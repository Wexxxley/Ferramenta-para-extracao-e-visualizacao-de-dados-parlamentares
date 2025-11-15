import math
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import Session, desc, func, select
from api.tratamentoDados.database import get_session
from api.dtos.analise_dtos import DeputadoRankingDespesa, ResumoDeputado
from api.dtos.deputado_dtos import DeputadoResponse
from api.dtos.ranking_deputados_atuantes_dtos import DeputadoRankingDTO
from api.log.logger_config import get_logger
from api.models.deputado import Deputado
from api.models.votacao_proposicao import VotacaoProposicao
from api.models.voto_individual import VotoIndividual
from api.utils.pagination import PaginatedResponse, PaginationParams

from api.utils.querys import get_despesas_deputado_2024_subquery

logger = get_logger("deputados_logger", "log/deputados.log")

deputado_router = APIRouter(prefix="/deputado", tags=["Deputado"])

@deputado_router.get("/get_by_id/{deputado_id}")
def get_by_id(deputado_id: int, ano: int = Query(None, description="Ano do database"), 
              session: Session = Depends(get_session)):
    
    statement = select(Deputado).where(Deputado.id == deputado_id)
    deputado = session.exec(statement).first()

    if not deputado:
        logger.warning(f"Deputado com ID {deputado_id} nao encontrado.")
        raise HTTPException(status_code=404, detail=f"Deputado com ID {deputado_id} nao encontrado.")

    deputado_response = DeputadoResponse.from_model(deputado)

    return deputado_response

@deputado_router.get("/get_all")
def get_all(
    pagination: PaginationParams = Depends(),
    session: Session = Depends(get_session),
    uf: Optional[str] = Query(None, description="Filtrar por sigla da UF (ex: PR, SP)"),
    sexo: Optional[str] = Query(None, description="Filtrar por sexo (M ou F)"),
    partido: Optional[str] = Query(None, description="Filtrar por sigla do partido (ex: PT, PL)")
):
    statement = select(Deputado)

    if uf:
        statement = statement.where(Deputado.sigla_uf == uf.upper())
    if sexo:
        statement = statement.where(Deputado.sexo == sexo.upper())
    if partido:
        statement = statement.where(Deputado.sigla_partido == partido.upper())

    count_statement = select(func.count()).select_from(statement.subquery())
    total = session.exec(count_statement).one()

    offset = (pagination.page - 1) * pagination.per_page
    deputados_statement = statement.offset(offset).limit(pagination.per_page)
    
    deputados_db = session.exec(deputados_statement).all()

    items_response = [
        DeputadoResponse.from_model(dep)
        for dep in deputados_db
    ]

    return PaginatedResponse(
        items=items_response, 
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        total_pages=math.ceil(total / pagination.per_page) if total > 0 else 0
    )

@deputado_router.get("/deputados/{id_deputado}/resumo")
def get_resumo_deputado(id_deputado: int, session: Session = Depends(get_session)):
    """
    Retorna um resumo de um deputado específico, com seu gasto total em 2024 e o número de sessões que votou. 

    Entidades: Deputado e VotoIndividual.
    """
    
    despesas_subq = get_despesas_deputado_2024_subquery()
    gasto_statement = select(despesas_subq.c.total_despesas).where(despesas_subq.c.id_deputado == id_deputado)
    total_gasto = session.exec(gasto_statement).first() or 0.0

    sessoes_votadas_statement = select(func.count(VotoIndividual.id_votacao.distinct())).where(VotoIndividual.id_deputado == id_deputado)
    sessoes_votadas = session.exec(sessoes_votadas_statement).one()
    
    return ResumoDeputado(
        id=id_deputado,
        sessoes_votadas=sessoes_votadas,
        total_gasto_2024=total_gasto
    )

@deputado_router.get("/ranking/deputados_despesa")
def get_ranking_deputados_despesa(pagination: PaginationParams = Depends(), session: Session = Depends(get_session)):
    """
    Retorna um ranking paginado de deputados com base no total de suas despesas em 2024, do maior para o menor. 
    Entidades: Deputado e Despesa
    """
    despesas_subq = get_despesas_deputado_2024_subquery()

    statement = (
        select(
            Deputado,
            func.coalesce(despesas_subq.c.total_despesas, 0.0).label("total_despesas")
        )
        .join(despesas_subq, Deputado.id == despesas_subq.c.id_deputado, isouter=True)
        .order_by(desc(func.coalesce(despesas_subq.c.total_despesas, 0.0)))
    )
    
    count_statement = select(func.count()).select_from(statement.subquery())
    total = session.exec(count_statement).one()

    offset = (pagination.page - 1) * pagination.per_page
    analise_statement = statement.offset(offset).limit(pagination.per_page)

    results = session.exec(analise_statement).all()

    ranking = [
        DeputadoRankingDespesa(
            id=dep.id,
            id_dados_abertos=dep.id_dados_abertos,
            nome_eleitoral=dep.nome_eleitoral,
            sigla_partido=dep.sigla_partido,
            sigla_uf=dep.sigla_uf,
            url_foto=dep.url_foto,
            sexo=dep.sexo,
            total_despesas= round(total_despesas, 2)
        )
        for dep, total_despesas in results
    ]
    
    return PaginatedResponse(
        items=ranking, 
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        total_pages=math.ceil(total / pagination.per_page) if total > 0 else 0
    )

@deputado_router.get("/ranking/atuantes", response_model=PaginatedResponse[DeputadoRankingDTO])
def get_ranking_deputados__mais_atuantes(
    pagination: PaginationParams = Depends(),
    session: Session = Depends(get_session)
):
    """
    Obtém um ranking paginado dos deputados mais atuantes com base em sua participação em votações.

    A "atuação" é medida pelo número total de sessões de votação distintas em que o 
    deputado participou. O endpoint também retorna o número de proposições únicas votadas como 
    uma métrica secundária.

    Entidades: Deputado, VotoIndividual e VotacaoProposicao
    """
    stmt = (
        select(
            Deputado.id,
            Deputado.nome_eleitoral,
            Deputado.sigla_partido,
            Deputado.sigla_uf,
            func.count(func.distinct(VotoIndividual.id_votacao)).label("total_votacoes"),
            func.count(func.distinct(VotacaoProposicao.id_proposicao)).label("total_proposicoes")
        )
        .join(VotoIndividual, VotoIndividual.id_deputado == Deputado.id)
        .join(VotacaoProposicao, VotacaoProposicao.id_votacao == VotoIndividual.id_votacao)
        .group_by(Deputado.id)
        .order_by(func.count(func.distinct(VotoIndividual.id_votacao)).desc())
        .offset((pagination.page - 1) * pagination.per_page)
        .limit(pagination.per_page)
    )

    results = session.exec(stmt).all()

    count_stmt = (
        select(func.count(func.distinct(Deputado.id)))
        .join(VotoIndividual, VotoIndividual.id_deputado == Deputado.id)
        .join(VotacaoProposicao, VotacaoProposicao.id_votacao == VotoIndividual.id_votacao)
    )

    total = session.exec(count_stmt).one()

    items = [
        DeputadoRankingDTO(
            id=r[0],
            nome_eleitoral=r[1],
            sigla_partido=r[2],
            sigla_uf=r[3],
            total_votacoes=r[4],
            total_proposicoes=r[5]
        ) for r in results
    ]

    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        total_pages=(total // pagination.per_page + int(total % pagination.per_page > 0))
    )
