import requests
import zipfile
import json
import os
from typing import Optional
from sqlmodel import Session, select
from ..models.despesa import Despesa
from ..models.deputado import Deputado
import os
import requests

# Faz o download do arquivo de despesas de um ano, descompacta e salva em data
def download_and_unzip_local_despesas(ano: int, http_session: requests.Session, progress_callback) -> Optional[str]:
    DATA_DIR = "data"
    os.makedirs(DATA_DIR, exist_ok=True)

    zip_filename = f"despesas_{ano}.json.zip"
    zip_filepath = os.path.join(DATA_DIR, zip_filename)
    json_filename = f"despesas_{ano}.json"
    json_filepath = os.path.join(DATA_DIR, json_filename)

    # 1. Baixa o ZIP se não existir
    if not os.path.exists(zip_filepath):
        progress_callback('log', f"   - Baixando arquivo ZIP de despesas para o ano {ano}...")
        
        url = f"http://www.camara.leg.br/cotas/Ano-{ano}.json.zip"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        try:
            response = http_session.get(url, headers=headers, timeout=300, stream=True)
            response.raise_for_status()

            with open(zip_filepath, 'wb') as f:
                f.write(response.content)
            progress_callback('log', f"   - ZIP salvo em '{zip_filepath}'")
        except requests.exceptions.RequestException as e:
            progress_callback('log', f"   - ERRO: Falha no download do ZIP para o ano {ano}. Detalhes: {e}")
            if os.path.exists(zip_filepath):
                os.remove(zip_filepath)
            return None
    else:
        progress_callback('log', f"   - Arquivo '{zip_filepath}' já existe localmente.")

    # 2. Descompacta o ZIP para JSON se ainda não existir
    if not os.path.exists(json_filepath):
        progress_callback('log', f"   - Descompactando ZIP para '{json_filepath}'...")
        try:
            with zipfile.ZipFile(zip_filepath, 'r') as arquivo_zip:
                nome_interno = arquivo_zip.namelist()[0]                
                caminho_extraido = arquivo_zip.extract(nome_interno, path=DATA_DIR)
                os.rename(caminho_extraido, json_filepath)
            progress_callback('log', f"   - Arquivo JSON salvo em '{json_filepath}'")
        except (zipfile.BadZipFile, IndexError) as e:
            progress_callback('log', f"   - ERRO: Falha na descompactação do ZIP para o ano {ano}. Detalhes: {e}")
            if os.path.exists(json_filepath):
                os.remove(json_filepath)
            return None
    else:
        progress_callback('log', f"   - Arquivo '{json_filepath}' já existe localmente.")

    return json_filepath


#  Verifica se já existem despesas para o ano. Se não, baixa o arquivo, processa e salva todas as despesas daquele ano.
def fetch_and_save_despesas(session: Session, http_session: requests.Session, ano: int, progress_callback):
    progress_callback('log', f"-> Iniciando processamento de despesas para o ano {ano}...")

    stmt_verificacao = select(Despesa)
    despesa_existente = session.exec(stmt_verificacao).first()

    if despesa_existente:
        progress_callback('log', f"-> Despesas para o ano {ano} já constam no banco. Etapa concluída.")
        return 
    
    # Se o código continuar, significa que não há despesas para este ano e o processamento é necessário.
    progress_callback('log', f"   - Nenhuma despesa para {ano} encontrada. Iniciando coleta...")

    # --- 1. Garante que o arquivo de dados exista localmente ---
    caminho_arquivo_json = download_and_unzip_local_despesas(ano, http_session, progress_callback)
    if not caminho_arquivo_json:
        raise Exception(f"Não foi possível obter o arquivo de despesas para o ano {ano}.")

    # --- Otimizações pré-loop ---
    progress_callback('log', "   - Criando mapa de deputados para chaves estrangeiras...")
    stmt_deputados = select(Deputado.id, Deputado.id_dados_abertos)
    mapa_deputados = {id_dados_abertos: id_db for id_db, id_dados_abertos in session.exec(stmt_deputados).all()}
    
    # --- Carrega e processa o arquivo JSON ---
    progress_callback('log', f"   - Lendo arquivo local '{caminho_arquivo_json}'...")
    with open(caminho_arquivo_json, 'r', encoding='utf-8-sig') as f: # Usando utf-8-sig por segurança
        dados = json.load(f)
    
    despesas_do_arquivo = dados.get('dados', [])
    total_despesas = len(despesas_do_arquivo)
    
    # --- Prepara uma lista para inserção em massa ---
    objetos_despesa_para_salvar = []
    
    for i, despesa in enumerate(despesas_do_arquivo):
        # Validação de dados essenciais
        valor_liquido = despesa.get('valorLiquido')
        id_deputado_api = despesa.get('idDeputado')
        if not valor_liquido or not id_deputado_api:
            continue
            
        id_deputado_fk = mapa_deputados.get(id_deputado_api)
        if id_deputado_fk is None:
            continue

        despesa_obj = Despesa(
            id_deputado=id_deputado_fk,
            ano=despesa.get('ano'),
            mes=despesa.get('mes'),
            tipo_despesa=despesa.get('tipoDespesa'), 
            valor_liquido=valor_liquido,
            tipo_documento=despesa.get('tipoDocumento'),
            url_documento=despesa.get('urlDocumento'),
            nome_fornecedor=despesa.get('nomeFornecedor') 
        )
        objetos_despesa_para_salvar.append(despesa_obj)
        
        if (i + 1) % 50000 == 0: 
            print(f"\r     {i + 1}/{total_despesas} registros verificados.", end="", flush=True)
        print()

    if objetos_despesa_para_salvar:
        progress_callback('log', f"   - Adicionando {len(objetos_despesa_para_salvar)} novas despesas à sessão...")
        session.add_all(objetos_despesa_para_salvar)

    progress_callback('log', "-> Processamento de despesas concluído.")