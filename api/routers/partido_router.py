from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import desc
from sqlmodel import Session, select, func
from typing import List
from typing import Optional

from api.dtos.analise_dtos import PartidoRankingDespesa
from api.tratamentoDados.database import get_session
from api.models.partido import Partido
from api.utils.pagination import PaginationParams, PaginatedResponse
import math
from api.models.deputado import Deputado
from sqlalchemy.orm import selectinload
from api.models.sessao_votacao import SessaoVotacao
from api.models.voto_individual import VotoIndividual
from api.utils.querys import get_despesas_deputado_2024_subquery

partido_router = APIRouter(prefix="/partido", tags=["Partido"])

# router get id
@partido_router.get("/get_by_id/{partido_id}", response_model=Partido)
def get_partido_by_id(partido_id: int, session: Session = Depends(get_session)):
    """
    Busca um partido específico pelo seu ID de banco de dados.
    """
    partido = session.get(Partido, partido_id)
    
    if not partido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partido com id {partido_id} não encontrado."
        )
    
    return partido

#router get all
@partido_router.get("/get_all", response_model=PaginatedResponse[Partido])
def get_all_partidos(
    pagination: PaginationParams = Depends(),
    session: Session = Depends(get_session),
    sigla: Optional[str] = Query(None),
    nome: Optional[str] = Query(None),
    situacao: Optional[str] = Query(None),
    min_membros: Optional[int] = Query(None, alias="min_membros"),
    max_membros: Optional[int] = Query(None, alias="max_membros")
):
    statement = select(Partido)

    if sigla:
        statement = statement.where(Partido.sigla.ilike(f"%{sigla}%"))
    if nome:
        statement = statement.where(Partido.nome_completo.ilike(f"%{nome}%"))
    if situacao:
        statement = statement.where(Partido.situacao.ilike(f"%{situacao}%"))
    if min_membros is not None:
        statement = statement.where(Partido.total_posse_legislatura >= min_membros)
    if max_membros is not None:
        statement = statement.where(Partido.total_posse_legislatura <= max_membros)

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

#router filtro deputado por sigla
@partido_router.get("/deputados_por_partido/{sigla_partido}", response_model=PaginatedResponse[Deputado])
def get_deputados_de_um_partido(
    sigla_partido: str,
    pagination: PaginationParams = Depends(),
    session: Session = Depends(get_session)
):
    """
    Obtém uma lista paginada de deputados de um partido específico,
    identificado pela sua sigla.
    """
    # Encontrar partido
    partido = session.exec(select(Partido).where(Partido.sigla == sigla_partido.upper())).first()

    if not partido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partido com a sigla '{sigla_partido}' não encontrado."
        )

    # Consulta com filtro de id
    statement = (
        select(Deputado)
        .where(Deputado.id_partido == partido.id)
        .options(selectinload(Deputado.gabinete)) # Carrega os dados do gabinete junto
    )

    # Aplica contagem pag
    count_statement = select(func.count()).select_from(statement.subquery())
    total = session.exec(count_statement).one()

    offset = (pagination.page - 1) * pagination.per_page
    deputados_db = session.exec(statement.offset(offset).limit(pagination.per_page)).all()

    # Retorna lista de dep
    return PaginatedResponse(
        items=deputados_db,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        total_pages=math.ceil(total / pagination.per_page) if total > 0 else 0
    )



@partido_router.get("/coesao_voto/{sigla_partido}/{id_votacao}")
def get_coesao_partido_em_votacao(
    sigla_partido: str,
    id_votacao: int,
    session: Session = Depends(get_session)
):
    """
    Analisa a distribuição de votos de um partido específico em uma determinada sessão de votação.
    Retorna a contagem e o percentual para cada tipo de voto (Sim, Não, Abstenção, etc.).

    Entidades: Partido, Deputado, VotoIndividual, SessaoVotacao
    """
    #Validar existencias
    partido = session.exec(select(Partido).where(Partido.sigla == sigla_partido.upper())).first()
    if not partido:
        raise HTTPException(status_code=404, detail=f"Partido com sigla '{sigla_partido}' não encontrado.")

    votacao = session.get(SessaoVotacao, id_votacao)
    if not votacao:
        raise HTTPException(status_code=404, detail=f"Votação com ID {id_votacao} não encontrada.")

    # Contrução de query para votação
    stmt = (
        select(VotoIndividual.tipo_voto, func.count(VotoIndividual.id).label("total"))
        .join(Deputado, Deputado.id == VotoIndividual.id_deputado)
        .where(Deputado.id_partido == partido.id)
        .where(VotoIndividual.id_votacao == id_votacao)
        .group_by(VotoIndividual.tipo_voto)
    )

    resultados_votos = session.exec(stmt).all()

    # Formatar para dicionario
    total_votantes_partido = sum(r.total for r in resultados_votos)
    distribuicao = []
    if total_votantes_partido > 0:
        distribuicao = [
            {
                "tipo_voto": r.tipo_voto,
                "total": r.total,
                "percentual": round((r.total / total_votantes_partido) * 100, 2)
            } for r in resultados_votos
        ]

    return {
        "sigla_partido": partido.sigla,
        "id_votacao": votacao.id,
        "descricao_votacao": votacao.descricao,
        "total_votantes_partido": total_votantes_partido,
        "distribuicao_votos": distribuicao
    }

@partido_router.get("/ranking/partidos_despesa")
def get_ranking_partidos_despesa(session: Session = Depends(get_session)):
    """
    Retorna um ranking de partidos ordenado pela soma total das despesas de seus deputados em 2024. 
    
    Entidades: Partido, Deputado e Despesa.
    """
    
    despesas_subq = get_despesas_deputado_2024_subquery()
    
    statement = (
        select(
            Partido,
            func.sum(despesas_subq.c.total_despesas).label("total_geral_partido")
        )
        .join(Deputado, Partido.id == Deputado.id_partido)
        .join(despesas_subq, Deputado.id == despesas_subq.c.id_deputado)
        .group_by(Partido.id)
        .order_by(desc("total_geral_partido"))
    )
    
    results = session.exec(statement).all()

    ranking = [
        PartidoRankingDespesa(
            id= partido.id,
            id_dados_abertos = partido.id_dados_abertos,
            sigla=partido.sigla,
            nome_completo=partido.nome_completo,
            total_despesas=round(total)
        )
        for partido, total in results
    ]
    return ranking


@partido_router.get("/ranking/partidos_por_tipo_voto")
def get_ranking_partidos_por_voto(
    tipo_voto: str = Query(..., description="Tipo de voto a ser contado (ex: 'Sim', 'Não', 'Abstenção', 'Obstrução')."),
    ano: Optional[int] = Query(None, description="Filtrar por ano específico."),
    pagination: PaginationParams = Depends(),
    session: Session = Depends(get_session)
):
    """
    Cria um ranking de partidos com base na contagem total de um tipo de voto específico.
    Permite filtrar por ano.
    """
    stmt = (
        select(
            Partido.sigla,
            Partido.nome_completo,
            func.count(VotoIndividual.id).label("total_votos")
        )
        .join(Deputado, Partido.id == Deputado.id_partido)
        .join(VotoIndividual, Deputado.id == VotoIndividual.id_deputado)
        .where(VotoIndividual.tipo_voto == tipo_voto)
    )

    if ano:
        stmt = stmt.where(func.cast(VotoIndividual.data_hora_registro, str).startswith(str(ano)))

    stmt = stmt.group_by(Partido.sigla, Partido.nome_completo).order_by(desc("total_votos"))
    
    count_subquery = select(func.count(func.distinct(Partido.id))).select_from(stmt.subquery())
    total = session.exec(count_subquery).one()

    offset = (pagination.page - 1) * pagination.per_page
    paginated_stmt = stmt.offset(offset).limit(pagination.per_page)
    
    resultados = session.exec(paginated_stmt).all()

    items = [
        {
            "sigla_partido": sigla,
            "nome_partido": nome,
            "tipo_voto_contado": tipo_voto,
            "total_votos": total_votos
        } for sigla, nome, total_votos in resultados
    ]

    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        total_pages=math.ceil(total / pagination.per_page) if total > 0 else 0
    )    