import requests
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from sqlmodel import Session, select
from ..models.voto_individual import VotoIndividual
from ..models.deputado import Deputado
from ..models.sessao_votacao import SessaoVotacao

#  Busca os votos individuais de UMA sessão de votação e retorna a lista de votos
def buscar_votos_por_sessao(uri_sessao: str, http_session: requests.Session) -> List[Dict]:
    try:
        url_votos = f"{uri_sessao}/votos"
        response = http_session.get(url_votos, headers={'accept': 'application/json'}, timeout=30)
        response.raise_for_status()
        return response.json().get('dados', [])
    except requests.exceptions.RequestException:
        return []

#  Busca os votos individuais para todas as sessões de um ano de forma concorrente e otimizada.
def fetch_and_save_votos(session: Session, http_session: requests.Session, ano: int, progress_callback):
    progress_callback('log', f"-> Iniciando processamento de votos individuais para o ano {ano}...")

    stmt_verificacao = select(VotoIndividual)
    votos_existente = session.exec(stmt_verificacao).first()

    if votos_existente:
        progress_callback('log', f"-> Votos para o ano {ano} já constam no banco. Etapa concluída.")
        return 

    # --- 1. Otimizações pré-loop: Carregar dados do DB em memória ---
    progress_callback('log', "   - Carregando dados do banco para otimização...")
    
    # a) Busca apenas as sessões do ano de interesse do nosso banco
    stmt_sessoes = select(SessaoVotacao).where(SessaoVotacao.data_hora_registro.like(f'{ano}%'))
    sessoes_do_ano_db = session.exec(stmt_sessoes).all()
    
    # b) Cria um mapa de id_dados_abertos -> objeto Deputado completo
    mapa_deputados = {dep.id_dados_abertos: dep for dep in session.exec(select(Deputado)).all()}

    # c) Pega os votos que já existem para as sessões deste ano para evitar duplicatas
    ids_sessoes_db = [s.id for s in sessoes_do_ano_db]
    stmt_existentes = select(VotoIndividual.id_votacao, VotoIndividual.id_deputado).where(VotoIndividual.id_votacao.in_(ids_sessoes_db))
    votos_existentes = set(session.exec(stmt_existentes).all())
    
    if not sessoes_do_ano_db:
        progress_callback('log', "   - Nenhuma sessão de votação encontrada no banco para este ano.")
        return

    # --- 2. Busca CONCORRENTE dos votos de todas as sessões ---
    progress_callback('log', f"   - Buscando votos para {len(sessoes_do_ano_db)} sessões simultaneamente...")
    uris_sessoes = [s.uri for s in sessoes_do_ano_db]
    
    mapa_sessao_para_votos = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        buscar_com_sessao = partial(buscar_votos_por_sessao, http_session=http_session)
        resultados_votos = executor.map(buscar_com_sessao, uris_sessoes)
        
        total_sessoes_a_buscar = len(uris_sessoes)
        for i, (sessao_db, lista_de_votos) in enumerate(zip(sessoes_do_ano_db, resultados_votos)):
            mapa_sessao_para_votos[sessao_db.id] = lista_de_votos
            
            if (i + 1) % 100 == 0 or (i + 1) == total_sessoes_a_buscar:
                print(f"\r      Buscando votos das sessões: {i + 1}/{total_sessoes_a_buscar}", end="", flush=True)
        print()

    # --- 3. Itera sobre os resultados e salva os votos novos ---
    progress_callback('log', "   - Processando e salvando novos votos...")
    objetos_voto_para_salvar = []
    
    for sessao_db in sessoes_do_ano_db:
        lista_de_votos_api = mapa_sessao_para_votos.get(sessao_db.id, [])
        
        for voto_api in lista_de_votos_api:
            deputado_info = voto_api.get('deputado_')
            if not deputado_info or not deputado_info.get('id'):
                continue
                
            id_deputado_api = int(deputado_info.get('id'))
            deputado_db = mapa_deputados.get(id_deputado_api)

            if deputado_db is None:
                continue # Pula voto se o deputado não estiver no nosso banco
            
            if (sessao_db.id, deputado_db.id) in votos_existentes:
                continue

            novo_voto = VotoIndividual(
                id_votacao=sessao_db.id,
                id_deputado=deputado_db.id,
                tipo_voto=voto_api.get('tipoVoto'),
                data_hora_registro=voto_api.get("dataRegistroVoto"),
                sigla_partido_deputado=deputado_db.sigla_partido,
                uri_deputado=deputado_info.get('uri'),
                uri_sessao_votacao=sessao_db.uri
            )
            objetos_voto_para_salvar.append(novo_voto)
            votos_existentes.add((sessao_db.id, deputado_db.id))
    
    if objetos_voto_para_salvar:
        progress_callback('log', f"   - Adicionando {len(objetos_voto_para_salvar)} novos registros de votos à sessão...")
        session.add_all(objetos_voto_para_salvar)

    progress_callback('log', "-> Processamento de votos individuais concluído.")