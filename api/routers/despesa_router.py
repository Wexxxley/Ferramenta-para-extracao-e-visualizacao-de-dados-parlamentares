from http import HTTPStatus
import math
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import Session, func, select
from api.tratamentoDados.database import get_session
from api.models.despesa import Despesa
from api.utils.pagination import PaginatedResponse, PaginationParams


despesa_router = APIRouter(prefix="/despesa", tags=["Despesa"])

@despesa_router.get("/get_by_id/{despesa_id}")
def get_despesa_by_id(despesa_id: int, session: Session = Depends(get_session)):

    despesa = session.get(Despesa, despesa_id)
    if not despesa:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Despesa com ID {despesa_id} não encontrada.")
    return despesa

@despesa_router.get("/get_all")
def get_all_despesas(
    pagination: PaginationParams = Depends(),
    session: Session = Depends(get_session),
    id_deputado: Optional[int] = Query(None, description="Filtrar despesas por ID do deputado."),
    ano: Optional[int] = Query(None, description="Filtrar despesas por ano."),
    mes: Optional[int] = Query(None, description="Filtrar despesas por mês.")
):

    statement = select(Despesa)
    if id_deputado:
        statement = statement.where(Despesa.id_deputado == id_deputado)
    if ano:
        statement = statement.where(Despesa.ano == ano)
    if mes:
        statement = statement.where(Despesa.mes == mes)

    count_statement = select(func.count()).select_from(statement.subquery())
    total = session.exec(count_statement).one()

    offset = (pagination.page - 1) * pagination.per_page
    despesas_statement = statement.offset(offset).limit(pagination.per_page)
    despesas = session.exec(despesas_statement).all()

    return PaginatedResponse(
        items=despesas,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        total_pages=math.ceil(total / pagination.per_page) if total > 0 else 0
    )
