from functools import partial
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor
from sqlmodel import Session, select
from ..models.deputado import Deputado
from ..models.partido import Partido

# Busca os detalhes do deputado via xml
def buscar_detalhes_deputado_xml(uri: str,  http_session: requests.Session) -> Optional[Dict]:
    try:
        headers = {'accept': 'application/xml'}
        response = http_session.get(uri, headers=headers, timeout=(5, 30))
        response.raise_for_status()

        root = ET.fromstring(response.content)
        dados = root.find('.//dados')
        if not dados:
            return None

        # Coleta os detalhes do deputado e do gabinete
        detalhes = {
            "nome_civil": dados.findtext('nomeCivil'),
            "nome_eleitoral": dados.findtext('ultimoStatus/nomeEleitoral'),
            "sexo": dados.findtext('sexo'),
            "sigla_partido": dados.findtext('ultimoStatus/siglaPartido'),
            "gabinete": {
                "nome": dados.findtext('ultimoStatus/gabinete/nome'),
                "predio": dados.findtext('ultimoStatus/gabinete/predio'),
                "sala": dados.findtext('ultimoStatus/gabinete/sala'),
                "andar": dados.findtext('ultimoStatus/gabinete/andar'),
                "telefone": dados.findtext('ultimoStatus/gabinete/telefone'),
                "email": dados.findtext('ultimoStatus/gabinete/email')
            }
        }
        return detalhes
            
    except (requests.exceptions.RequestException, ET.ParseError) as e:
        print(f"  - Falha ao buscar ou analisar detalhes da URI {uri}: {e}")
        return None

# Realiza as requições de todos os deputados de uma legislatura (4 anos) e salva os dados
def fetch_and_save_deputados(session: Session, http_session: requests.Session, id_legislatura: int, progress_callback):
    progress_callback('log', f"-> Iniciando busca de deputados para a Legislatura nº {id_legislatura}...")

    stmt_verificacao = select(Deputado)
    deputados_existente = session.exec(stmt_verificacao).first()

    if deputados_existente:
        progress_callback('log', f"-> Deputado para a legislatura {id_legislatura} já constam no banco. Etapa concluída.")
        return 

    # --- 1. Busca a lista base de deputados da API (com paginação) ---
    deputados_base = []
    url = f"https://dadosabertos.camara.leg.br/api/v2/deputados?idLegislatura={id_legislatura}&itens=100&ordem=ASC&ordenarPor=nome"
    
    while url:
        try:
            response = http_session.get(url, timeout=(5, 30))
            response.raise_for_status()
            dados = response.json()
            deputados_base.extend(dados.get('dados', []))
            url = next((link['href'] for link in dados['links'] if link['rel'] == 'next'), None)
        except requests.exceptions.RequestException as e:
            progress_callback('log', "ERRO CRÍTICO: Não foi possível buscar a lista de deputados. {e}")
            return

    progress_callback("log",f"   - Encontrados {len(deputados_base)} registros de deputados na legislatura.")

    # Usamos um dicionário para garantir que cada ID de deputado apareça apenas uma vez.
    deputados_unicos_dict = {dep['id']: dep for dep in deputados_base}
    
    # Convertemos os valores do dicionário de volta para uma lista.
    deputados_base_unicos = list(deputados_unicos_dict.values())
    progress_callback("log", f"   - Total de {len(deputados_base_unicos)} deputados únicos para processar.")

    # --- Otimizações pré-loop ---
    stmt_existentes = select(Deputado.id_dados_abertos)
    ids_deputados_existentes = set(session.exec(stmt_existentes).all())
    progress_callback("log",f"   - Encontrados {len(ids_deputados_existentes)} deputados já existentes no banco.")

    stmt_partidos = select(Partido.id, Partido.sigla)
    mapa_partidos = {sigla: id for id, sigla in session.exec(stmt_partidos).all()}

    # --- 2. Busca todos os detalhes de forma concorrente ---
    deputados_a_processar = [p for p in deputados_base_unicos if p.get('id') not in ids_deputados_existentes]
    uris_para_buscar = [p.get('uri') for p in deputados_a_processar if p.get('uri')]
    
    if not uris_para_buscar:
        print("Nenhum deputado novo para processar.")
        print("Processamento de deputados concluído.")
        return

    progress_callback("log", f"   - Buscando detalhes para {len(uris_para_buscar)} novos deputados simultaneamente...")

    # --- Detalhes sendo buscados de forma paralela
    with ThreadPoolExecutor(max_workers=10) as executor:
        buscar_com_sessao = partial(buscar_detalhes_deputado_xml, http_session=http_session)
        detalhes_dos_deputados =  list(executor.map(buscar_com_sessao, uris_para_buscar))

    # --- 3. Itera sobre os resultados combinados e cria os objetos do modelo ---
    progress_callback("log", "   - Combinando dados e preparando para salvar...")
    for deputado_info, detalhes_deputado in zip(deputados_a_processar, detalhes_dos_deputados):
        if detalhes_deputado:
            sigla_partido = detalhes_deputado.get("sigla_partido")
            id_partido_fk = mapa_partidos.get(sigla_partido)

            deputado_obj = Deputado(
                id_dados_abertos=deputado_info.get('id'),
                nome_civil=detalhes_deputado.get('nome_civil'),
                nome_eleitoral=detalhes_deputado.get('nome_eleitoral'),
                sigla_partido=sigla_partido,
                id_partido=id_partido_fk,
                sigla_uf=deputado_info.get('siglaUf'),
                sexo=detalhes_deputado.get('sexo'),
                id_legislativo=deputado_info.get('idLegislatura'),
                url_foto=deputado_info.get('urlFoto')
            )
            session.add(deputado_obj)
        else:
            progress_callback("log", f"  - Falha ao obter detalhes para o deputado {deputado_info.get('nome')}. Pulando.")
    
    progress_callback("log", "-> Processamento de deputados concluído.")