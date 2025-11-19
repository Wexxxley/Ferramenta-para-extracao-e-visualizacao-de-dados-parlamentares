from fastapi import HTTPException, APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import Optional
import math
from api.models.sessao_votacao import SessaoVotacao
from api.tratamentoDados.database import get_session
from api.utils.pagination import PaginatedResponse, PaginationParams

sessaovotacao_router = APIRouter(  
    prefix="/sessaovotacao",
    tags=["SessaoVotacao"]
)

# Obtém uma sessão de votação pelo ID
@sessaovotacao_router.get("/get_by_id/{id}")
def get_by_id(id: int, session: Session = Depends(get_session)):
    sessao = session.get(SessaoVotacao, id)
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão de votação não encontrada.")
    return sessao

# Obtém todas as sessões de votação com paginação e filtros opcionais
@sessaovotacao_router.get("/get_all")
def get_all_sessoes(
    pagination: PaginationParams = Depends(),
    session: Session = Depends(get_session),
    sigla_orgao: Optional[str] = Query(None)
):
    statement = select(SessaoVotacao)
    if sigla_orgao:
        statement = statement.where(SessaoVotacao.sigla_orgao == sigla_orgao.upper())

    count = session.exec(select(func.count()).select_from(statement.subquery())).one()[0]
    offset = (pagination.page - 1) * pagination.per_page

    results = session.exec(statement.offset(offset).limit(pagination.per_page)).scalars().all()

    return PaginatedResponse(
        items=results,
        total=count,
        page=pagination.page,
        per_page=pagination.per_page,
        total_pages=math.ceil(count / pagination.per_page) if count > 0 else 0
    )