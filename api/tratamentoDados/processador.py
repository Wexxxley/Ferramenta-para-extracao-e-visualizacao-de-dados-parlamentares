import time
from sqlmodel import Session 
from .database import create_db_and_tables, get_engine_for_year, create_session_with_retries
from .despesaProcessor import download_and_unzip_local_despesas, fetch_and_save_despesas
from .partidoProcessor import fetch_and_save_partidos
from .deputadosProcessor import fetch_and_save_deputados
from .sessaoProposicaoProcessor import fetch_and_save_votacoes
from .votoProcessor import buscar_votos_por_sessao, fetch_and_save_votos

def run_data_processing(year: int, progress_callback):
    # --- MEDIÇÃO DE TEMPO INÍCIO TOTAL ---
    inicio_total = time.perf_counter()
    progress_callback('log', "="*50)
    progress_callback('log', f"Iniciando coleta para o ano de {year}...")
    progress_callback('progress', 5)

    # --- 1. Determina a Legislatura ---
    if 2011 <= year < 2015: legislatura = 54
    elif 2015 <= year < 2019: legislatura = 55
    elif 2019 <= year < 2023: legislatura = 56
    elif 2023 <= year <= 2027: legislatura = 57
    else:
        progress_callback('log', f"ERRO: Ano {year} fora do intervalo analisado (2011-2027).")
        return False

    # --- 2. Configura o Banco de Dados e a SESSÃO DE REQUISIÇÕES ---
    try:
        engine = get_engine_for_year(year)
        create_db_and_tables(engine)
        progress_callback('log', f"Banco de dados 'dbs/camara_{year}.db' está pronto.")
        http_session = create_session_with_retries()
        progress_callback('progress', 10)
    except Exception as e:
        progress_callback('log', f"ERRO CRÍTICO ao configurar o ambiente: {e}")
        return False
        
    # --- 3. Executa a Coleta e Salva os Dados ---
    with Session(engine) as session:
        try:
            # --- PROCESSANDO PARTIDOS ---
            inicio_partidos = time.perf_counter()
            fetch_and_save_partidos(session, http_session, progress_callback)
            duracao_partidos = time.perf_counter() - inicio_partidos
            progress_callback('log', f"⏱️ Tempo de processamento dos partidos: {duracao_partidos:.2f} segundos.\n")
            progress_callback('progress', 25)
            
            # --- PROCESSANDO DEPUTADOS ---
            inicio_deputados = time.perf_counter()
            fetch_and_save_deputados(session, http_session, legislatura, progress_callback)
            duracao_deputados = time.perf_counter() - inicio_deputados
            progress_callback('log', f"⏱️ Tempo de processamento dos deputados: {duracao_deputados:.2f} segundos.\n")
            progress_callback('progress', 40)

            # --- PROCESSANDO DESPESAS ---
            inicio_despesas = time.perf_counter()
            fetch_and_save_despesas(session, http_session, year, progress_callback)
            duracao_despesas = time.perf_counter() - inicio_despesas
            progress_callback('log', f"⏱️ Tempo de processamento das despesas: {duracao_despesas:.2f} segundos.\n")
            progress_callback('progress', 60)

            # --- PROCESSANDO SESSAO ---
            inicio_sessoes = time.perf_counter()
            fetch_and_save_votacoes(session, http_session, year, progress_callback)
            duracao_sessoes = time.perf_counter() - inicio_sessoes
            progress_callback('log', f"⏱️ Tempo de processamento das sessoes de votacao: {duracao_sessoes:.2f} segundos.\n")
            progress_callback('progress', 80)
            
            # --- PROCESSANDO VOTO ---
            inicio_votos = time.perf_counter()
            fetch_and_save_votos(session, http_session, year, progress_callback)
            duracao_votos = time.perf_counter() - inicio_votos
            progress_callback('log', f"⏱️ Tempo de processamento das sessoes de votacao: {duracao_votos:.2f} segundos.\n")
            progress_callback('progress', 95)
            progress_callback('log', "Coleta finalizada. Salvando dados no banco...")
            session.commit()
            progress_callback('log', "Dados salvos com sucesso!")
            
        except Exception as e:
            progress_callback('log', f"ERRO durante a coleta de dados: {e}")
            session.rollback()
            return False

    # --- MEDIÇÃO DE TEMPO: FIM TOTAL ---
    fim_total = time.perf_counter()
    duracao_total = fim_total - inicio_total
    
    progress_callback('log', "="*50)
    progress_callback('log', f"✅ Processo Concluído!")
    progress_callback('log', f"⏳ Tempo Total de Execução: {duracao_total/60:.2f} minutos.")
    progress_callback('progress', 100)

    return True

def mock_progress_callback(msg_type, data):
    if msg_type == 'log':
        print(f"[LOG] {data}")
    elif msg_type == 'progress':
        print(f"[PROGRESS] {data}%")

if __name__ == '__main__':
    ano_para_teste = 2012
    run_data_processing(ano_para_teste, mock_progress_callback)