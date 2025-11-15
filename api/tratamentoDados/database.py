import os
import requests
from sqlmodel import SQLModel, create_engine, Session
from urllib3 import Retry
from requests.adapters import HTTPAdapter

DB_DIRECTORY = "dbs"

# Cria e retorna uma engine do SQLModel para um ano específico.
# O banco de dados será salvo em uma pasta 'dbs'.
def get_engine_for_year(year: int):
    # Garante que o diretório 'dbs' exista. Se não existir, ele será criado.
    os.makedirs(DB_DIRECTORY, exist_ok=True)
    db_filename = f"camara_{year}.db"
    db_filepath = os.path.join(DB_DIRECTORY, db_filename)
    
    # Cria a URL de conexão para o arquivo SQLite
    database_url = f"sqlite:///{db_filepath}"
    engine = create_engine(database_url)

    return engine

# Cria todas as tabelas definidas nos modelos para uma engine específica.
def create_db_and_tables(engine):
    SQLModel.metadata.create_all(engine)

# Cria uma sessão de requests configurada com timeouts e tentativas automáticas.
def create_session_with_retries() -> requests.Session:
    session = requests.Session()
    
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])    
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    return session

def get_session(year: int):

    engine = get_engine_for_year(year)
    
    with Session(engine) as session:
        yield session
