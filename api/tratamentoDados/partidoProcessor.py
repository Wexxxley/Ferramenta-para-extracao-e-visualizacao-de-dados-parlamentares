from collections import defaultdict
from functools import partial
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Optional
from sqlalchemy import select
from sqlmodel import Session
from ..models.partido import Partido
from collections import defaultdict 
from concurrent.futures import ThreadPoolExecutor

#Converte para inteiro
def to_int(value: Optional[str]) -> Optional[int]:
    if value is None or not value.isdigit():
        return None
    return int(value)

#Dado uma uri busca os detalhes de um partido em xml
def buscar_detalhes_partido_xml(uri: str, http_session: requests.Session) -> Optional[Dict]:
    try:
        headers = {'accept': 'application/xml'}
        response = http_session.get(uri, headers=headers, timeout=(5, 30))
        response.raise_for_status() 

        root = ET.fromstring(response.content)
        dados = root.find('.//dados')
        
        if dados is None:
            return None

        detalhes = {
            "uri_logo": dados.findtext('urlLogo'),
            "id_legislativo": to_int(dados.findtext('status/idLegislatura')),
            "situacao": dados.findtext('status/situacao'),
            "total_membros": to_int(dados.findtext('status/totalMembros')),
            "total_posse_legislatura": to_int(dados.findtext('status/totalPosse')),
        }
        return detalhes
            
    except requests.exceptions.RequestException as e:
        print(f"  - Erro de conexão ao acessar {uri}: {e}")
        return None
    except ET.ParseError:
        print(f"  - Falha ao analisar o XML da URI {uri}.")
        return None

# Realiza as requisicoes de todos os partidos (2011-2027) e salva os dados
def fetch_and_save_partidos(session: Session, http_session: requests.Session, progress_callback):
    progress_callback('log', "-> Iniciando busca de partidos para as legislaturas de 2011 em diante...")

    stmt_verificacao = select(Partido)
    partidos_existente = session.exec(stmt_verificacao).first()

    if partidos_existente:
        progress_callback('log', f"-> Partidos já constam no banco. Etapa concluída.")
        return 

    
    # --- 1. legislaturas de interesse
    legislaturas_alvo = [54, 55, 56, 57]
    partidos_brutos_agregados = []
    
    for leg in legislaturas_alvo:
        progress_callback('log', f"   - Buscando partidos da {leg}ª Legislatura...")
        uri = f"https://dadosabertos.camara.leg.br/api/v2/partidos?idLegislatura={leg}&itens=1000&ordem=ASC&ordenarPor=sigla"
        try:
            response = http_session.get(uri, headers={'accept': 'application/json'}, timeout=(5, 30))
            response.raise_for_status()
            partidos_da_legislatura = response.json().get('dados', [])
            partidos_brutos_agregados.extend(partidos_da_legislatura)
        except requests.exceptions.RequestException as e:
            progress_callback('log', f"   - AVISO: Falha ao buscar partidos da legislatura {leg}. Continuando... Erro: {e}")
            continue

    progress_callback('log', f"   - Coleta inicial concluída. Total de {len(partidos_brutos_agregados)} registros de partidos encontrados.")

    # --- Desduplica a lista para ter apenas partidos únicos ---
    partidos_unicos_dict = {p['id']: p for p in partidos_brutos_agregados}
    partidos_base = list(partidos_unicos_dict.values())
    progress_callback('log', f"   - {len(partidos_base)} partidos únicos identificados no período.")

    # --- Verifica quais partidos únicos já existem no banco
    stmt_existentes = select(Partido.id_dados_abertos)
    ids_partidos_existentes = {id_tuple[0] for id_tuple in session.exec(stmt_existentes).all()}
    partidos_novos = [p for p in partidos_base if p.get('id') not in ids_partidos_existentes]
    
    if not partidos_novos:
        progress_callback('log', "-> Nenhum partido novo para adicionar. Tabela já está atualizada.")
        progress_callback('log', "-> Processamento de partidos concluído.")
        return

    # --- Busca detalhes de forma concorrente apenas para os novos ---
    uris_para_buscar = [p.get('uri') for p in partidos_novos if p.get('uri')]
    progress_callback('log', f"   - Buscando detalhes para {len(uris_para_buscar)} novos partidos simultaneamente...")

    # --- Utiliza ate 25 treads para fazer as requisições de detalhes ---
    with ThreadPoolExecutor(max_workers=10) as executor:
        buscar_com_sessao = partial(buscar_detalhes_partido_xml, http_session=http_session)
        detalhes_dos_partidos = list(executor.map(buscar_com_sessao, uris_para_buscar))

    # --- Itera e cria os objetos do modelo para os novos partidos ---
    for partido_info, detalhes_partido in zip(partidos_novos, detalhes_dos_partidos):
        if detalhes_partido:
            partido_obj = Partido(
                id_dados_abertos=partido_info.get('id'),
                sigla=partido_info.get("sigla"),
                nome_completo=partido_info.get("nome"),
                uri_logo=detalhes_partido.get('uri_logo'),
                id_legislativo=detalhes_partido.get('id_legislativo'),
                situacao=detalhes_partido.get('situacao'),
                total_membros=detalhes_partido.get('total_membros'),
                total_posse_legislatura=detalhes_partido.get('total_posse_legislatura'),
            )
            session.add(partido_obj)

    progress_callback('log', "-> Processamento de partidos concluído.")