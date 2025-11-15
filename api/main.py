import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .routers.deputado_router import deputado_router
from .routers.analise_router import analise_router
from .routers.despesa_router import despesa_router
from .routers.sessao_votacao_router import sessaovotacao_router
from .routers.voto_individual_router import voto_router
from .routers.partido_router import partido_router
from .routers.proposicao_router import proposicao_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluindo as rotas
app.include_router(deputado_router)
app.include_router(despesa_router)
app.include_router(partido_router)
app.include_router(sessaovotacao_router)
app.include_router(voto_router)
app.include_router(proposicao_router)
app.include_router(analise_router)


# --- ADICIONE ESTE BLOCO DE CÓDIGO ---
# 2. Define o caminho para a pasta 'frontend'
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")

# 3. "Monta" a pasta, tornando-a acessível via HTTP
#    O path="" significa que o index.html será a página inicial do site
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
# --- FIM DO BLOCO ---
