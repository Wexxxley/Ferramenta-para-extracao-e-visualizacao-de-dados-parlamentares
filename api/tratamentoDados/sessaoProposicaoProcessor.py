import xml.etree.ElementTree as ET
import requests
import json
import os
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from sqlmodel import Session, select
from ..models.proposicao import Proposicao
from ..models.sessao_votacao import SessaoVotacao
from ..models.votacao_proposicao import VotacaoProposicao

# Faz o download do arquivo de sessoes de votação direto da api da camara
def download_votacoes_file(ano: int, http_session: requests.Session, progress_callback) -> Optional[str]:
    DATA_DIR = "data"
    os.makedirs(DATA_DIR, exist_ok=True)
    json_filename = f"votacoes_{ano}.json"
    json_filepath = os.path.join(DATA_DIR, json_filename)
    
    if os.path.exists(json_filepath):
        progress_callback('log', f"   - Arquivo '{json_filepath}' já existe localmente.")
        return json_filepath

    progress_callback('log', f"   - Baixando arquivo de votações para o ano {ano}...")
    url = f"https://dadosabertos.camara.leg.br/arquivos/votacoes/json/votacoes-{ano}.json"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = http_session.get(url, headers=headers, timeout=300)
        response.raise_for_status()
        with open(json_filepath, 'wb') as f:
            f.write(response.content)
        progress_callback('log', f"   - Arquivo salvo em '{json_filepath}'")
        return json_filepath
    except requests.exceptions.RequestException as e:
        progress_callback('log', f"   - ERRO: Falha no download do arquivo para {ano}. Detalhes: {e}")
        return None
    
# Busca os detalhes de UMA proposição
def buscar_detalhes_proposicao_api(proposicao_id: str, http_session: requests.Session) -> Optional[Dict]:
    try:
        url = f'https://dadosabertos.camara.leg.br/api/v2/proposicoes/{proposicao_id}'
        response = http_session.get(url, headers={'accept': 'application/json'}, timeout=15)
        response.raise_for_status()
        return response.json().get('dados', {})
    except requests.exceptions.RequestException:
        return None

# Busca o XML de uma votação e retorna a lista de IDs de proposições afetadas.
def buscar_ids_proposicoes_em_xml(uri: str, http_session: requests.Session) -> List[str]:
    try:
        response = http_session.get(uri, headers={'accept': 'application/xml'}, timeout=20)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        ids = [elem.text for elem in root.findall('.//proposicoesAfetadas/proposicoesAfetadas/id') if elem.text]
        return ids
    except (requests.exceptions.RequestException, ET.ParseError):
        return []

# Busca as sessoes de votação e as proposiçoes associdas e salva no db
def fetch_and_save_votacoes(session: Session, http_session: requests.Session, ano: int, progress_callback):
    
    progress_callback('log', f"-> Iniciando processamento de votações para o ano {ano}...")

    stmt_verificacao = select(SessaoVotacao)
    sessoes_existente = session.exec(stmt_verificacao).first()

    if sessoes_existente:
        progress_callback('log', f"-> Sessões para o ano {ano} já constam no banco. Etapa concluída.")
        return 

    caminho_arquivo = download_votacoes_file(ano, http_session, progress_callback)
    if not caminho_arquivo:
        raise Exception(f"Arquivo de votações para {ano} não pôde ser baixado.")

    try:
        with open(caminho_arquivo, 'r', encoding='utf-8-sig') as f:
            dados_completos = json.load(f)
        sessoes_base = dados_completos.get('dados', [])
    except json.JSONDecodeError as e:
        progress_callback('log', f"ERRO CRÍTICO: O arquivo '{caminho_arquivo}' não é um JSON válido. {e}")
        raise

    progress_callback('log', f"   - Encontradas {len(sessoes_base)} sessões no arquivo de {ano}.")

    # --- Verificando sessoes e proposicoes que já existem no DB ---
    ids_sessoes_existentes_db = {s for s in session.exec(select(SessaoVotacao.id_dados_abertos)).all()}   #set[id_dados_abertos]
    proposicoes_existentes_db = {str(p.id_dados_abertos): p for p in session.exec(select(Proposicao)).all()} #dict[id_dados_abertos, Proposicao]

    # --- Verificando no arquivo de sessoes quais eu vou precisar analisar ---
    sessoes_a_processar = [s for s in sessoes_base if str(s.get('id')) not in ids_sessoes_existentes_db]
    if not sessoes_a_processar:
        progress_callback('log', "-> Nenhuma nova sessão de votação para adicionar.")
        return
    
    uris_sessoes_para_processar = [s.get('uri') for s in sessoes_a_processar if s.get('uri')]


    # --- Busca CONCORRENTE dos IDs de proposições em todas as novas sessões ---
    progress_callback('log', f"   - Buscando proposições afetadas para {len(sessoes_a_processar)} novas sessões...")
    mapa_sessao_para_props = {}       # {id_da_sessao: [id_prop_1, id_prop_2]}
    ids_proposicoes_a_buscar = set()  # Vai guardar os IDs das proposições que são novas para nós
    
    with ThreadPoolExecutor(max_workers=25) as executor:
        buscar_com_sessao = partial(buscar_ids_proposicoes_em_xml, http_session=http_session)
        
        resultados_ids = executor.map(buscar_com_sessao, uris_sessoes_para_processar)
        
        total_sessoes = len(uris_sessoes_para_processar)
        for i, (sessao_dict, lista_de_ids_prop) in enumerate(zip(sessoes_a_processar, resultados_ids)):
            # Atualiza o progresso no terminal a cada 100 itens
            if (i + 1) % 100 == 0 or (i + 1) == total_sessoes:
                print(f"\r      Lendo XMLs de sessões: {i + 1}/{total_sessoes}", end="", flush=True)

            mapa_sessao_para_props[sessao_dict['id']] = lista_de_ids_prop
            for prop_id in lista_de_ids_prop:
                if prop_id not in proposicoes_existentes_db:
                    ids_proposicoes_a_buscar.add(prop_id)
        print()
            

    # --- Busca CONCORRENTE dos detalhes de todas as proposições novas ---
    if ids_proposicoes_a_buscar:
        progress_callback('log', f"   - Buscando detalhes para {len(ids_proposicoes_a_buscar)} novas proposições...")
        detalhes_proposicoes = [] # Inicia a lista vazia para preencher no loop
        with ThreadPoolExecutor(max_workers=10) as executor:
            buscar_com_sessao = partial(buscar_detalhes_proposicao_api, http_session=http_session)
            
            resultados_detalhes = executor.map(buscar_com_sessao, list(ids_proposicoes_a_buscar))
            
            total_proposicoes = len(ids_proposicoes_a_buscar)
            for i, detalhe in enumerate(resultados_detalhes):
                detalhes_proposicoes.append(detalhe)
                
                if (i + 1) % 50 == 0 or (i + 1) == total_proposicoes:
                    print(f"\r      Buscando detalhes de proposições: {i + 1}/{total_proposicoes}", end="", flush=True)

        print() 

        for prop_detalhes in detalhes_proposicoes:
            if prop_detalhes and prop_detalhes.get('id'):
                prop_id_str = str(prop_detalhes.get('id'))
                if prop_id_str not in proposicoes_existentes_db:
                    nova_proposicao = Proposicao(
                        id_dados_abertos=prop_id_str,
                        sigla_tipo=prop_detalhes.get('siglaTipo'),
                        ano=prop_detalhes.get('ano'),
                        ementa=prop_detalhes.get('ementa'),
                        data_apresentacao=prop_detalhes.get('dataApresentacao'),
                        status=prop_detalhes.get('statusProposicao', {}).get('descricaoSituacao'),
                        url_inteiro_teor=prop_detalhes.get('urlInteiroTeor')
                    )
                    session.add(nova_proposicao)
                    proposicoes_existentes_db[prop_id_str] = nova_proposicao
    
    # --- Adicionar as Sessões e criar os Links ---
    progress_callback('log', f"   - Adicionando {len(sessoes_a_processar)} novas sessões e seus links...")
    for sessao_dict in sessoes_a_processar:
        nova_sessao = SessaoVotacao(
            id_dados_abertos=sessao_dict.get('id'),
            data_hora_registro=sessao_dict.get('dataHoraRegistro'),
            descricao=sessao_dict.get('descricao'),
            sigla_orgao=sessao_dict.get('siglaOrgao'),
            uri=sessao_dict.get('uri'),
            aprovacao=str(sessao_dict.get('aprovacao')) if sessao_dict.get('aprovacao') is not None else None,
            descricao_ultima_abertura_votacao=sessao_dict.get('ultimaAberturaVotacao', {}).get('descricao')
        )
        session.add(nova_sessao)
        session.flush()

        ids_props_desta_sessao = mapa_sessao_para_props.get(sessao_dict.get('id'), [])
        for prop_id_str in ids_props_desta_sessao:
            proposicao_no_db = proposicoes_existentes_db.get(prop_id_str)
            if proposicao_no_db:
                link = VotacaoProposicao(id_votacao=nova_sessao.id, id_proposicao=proposicao_no_db.id)
                session.add(link)
    
    progress_callback('log', "-> Processamento de votações concluído.")