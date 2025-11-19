from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from api.tratamentoDados.database import get_session
from api.models.proposicao import Proposicao
from api.models.sessao_votacao import SessaoVotacao
from api.utils.pagination import PaginatedResponse, PaginationParams
import math
from typing import Optional
from api.dtos.proposicao_dtos import  ProposicaoMaisVotadaDTO
from api.models.votacao_proposicao import VotacaoProposicao

proposicao_router = APIRouter(prefix="/proposicao", tags=["Proposicao"])

# Obtém uma proposição pelo ID
@proposicao_router.get("/get_by_id/{id}")
def get_by_id(id: int, session: Session = Depends(get_session)):
    proposicao = session.get(Proposicao, id)
    if not proposicao:
        raise HTTPException(status_code=404, detail="Proposição não encontrada.")
    return proposicao

# Obtém todas as proposições com paginação e filtros opcionais
@proposicao_router.get("/get_all")
def get_all_proposicoes(
    pagination: PaginationParams = Depends(),
    session: Session = Depends(get_session),
    ano: Optional[int] = Query(None),
    sigla_tipo: Optional[str] = Query(None)
):
    statement = select(Proposicao)

    if ano:
        statement = statement.where(Proposicao.ano == ano)
    if sigla_tipo:
        statement = statement.where(Proposicao.sigla_tipo == sigla_tipo.upper())

    count_statement = select(func.count()).select_from(statement.subquery())
    total = session.exec(count_statement).one()

    offset = (pagination.page - 1) * pagination.per_page
    results = session.exec(statement.offset(offset).limit(pagination.per_page)).all()

    return PaginatedResponse(
        items=results,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        total_pages=math.ceil(total / pagination.per_page) if total > 0 else 0
    )


@proposicao_router.get("/{proposicao_id}/sessoes")
def get_sessoes_por_proposicao(
    proposicao_id: int, 
    session: Session = Depends(get_session)
):
    """
    Busca todas as sessões de votação associadas a uma proposição específica.
    Entidades: Votacao e VotacaoProposicao.
    """
    # 1. Opcional, mas recomendado: Verificar se a proposição existe primeiro
    proposicao = session.get(Proposicao, proposicao_id)
    if not proposicao:
        raise HTTPException(
            status_code=404, 
            detail=f"Proposição com ID {proposicao_id} não encontrada."
        )

    # 2. Monta a query para buscar as votações
    stmt = (
        select(SessaoVotacao)
        .join(VotacaoProposicao, VotacaoProposicao.id_votacao == SessaoVotacao.id)
        .where(VotacaoProposicao.id_proposicao == proposicao_id)
        .order_by(SessaoVotacao.data_hora_registro.desc())  # Opcional: ordena as mais recentes primeiro
    )

    sessoes = session.exec(stmt).all()
    
    return sessoes

@proposicao_router.get("/mais_votadas/{limite}", response_model=list[ProposicaoMaisVotadaDTO])
def get_proposicoes_mais_votadas(limite: int, session: Session = Depends(get_session)):
    """
    Retorna as 10 proposições mais votadas, com base no número de sessões de votação associadas. 
    Entidades: Proposicao, VotacaoProposicao.
    """
    stmt = (
        select(
            Proposicao.id,
            Proposicao.id_dados_abertos,
            Proposicao.sigla_tipo,
            Proposicao.ano,
            Proposicao.ementa,
            func.count(VotacaoProposicao.id_votacao).label("total_votacoes")
        )
        .join(VotacaoProposicao, VotacaoProposicao.id_proposicao == Proposicao.id)
        .group_by(Proposicao.id)
        .order_by(func.count(VotacaoProposicao.id_votacao).desc())
        .limit(limite)
    )

    results = session.exec(stmt).all()
    return results