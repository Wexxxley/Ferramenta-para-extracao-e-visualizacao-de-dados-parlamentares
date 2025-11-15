from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlmodel import Session, String, case, desc, func, select
from api.tratamentoDados.database import get_session
from api.log.logger_config import get_logger
from api.models.deputado import Deputado
from api.models.despesa import Despesa
from api.models.partido import Partido
from api.models.sessao_votacao import SessaoVotacao
from api.models.voto_individual import VotoIndividual

logger = get_logger("analises_logger", "log/analises.log")

analise_router = APIRouter(prefix="/analise", tags=["Analises complementares"])


@analise_router.get("/comparativo_estados")
async def comparativo_gastos_estados(
    year: int = Query(2024, description="Ano de referência para análise", ge=2000),
    uf: Optional[str] = Query(
        None,
        description="Filtrar por sigla de UF específica (ex: 'SP')",
        max_length=2,
        pattern="^[A-Z]{2}$"
    ),
    
    session: Session = Depends(get_session)
):
    """
    Agrupa os gastos parlamentares por estado, retornando o gasto 
    total, a média e a quantidade de despesas. 
    Entidades: `Deputado` e `Despesa`.
    """
    try:
        
        stmt = (
            select(
                Deputado.sigla_uf,
                func.sum(Despesa.valor_liquido).label("total_gasto"),
                func.avg(Despesa.valor_liquido).label("media_gasto"),
                func.count(Despesa.id).label("quantidade"),
                func.count(Deputado.id.distinct()).label("total_deputados")
            )
            .join(Despesa, Despesa.id_deputado == Deputado.id)
            .where(Despesa.ano == year)
        )

        if uf:
            stmt = stmt.where(Deputado.sigla_uf == uf.upper())

        stmt = stmt.group_by(Deputado.sigla_uf).order_by(desc("total_gasto"))
        results = session.exec(stmt).all()

        return [
            {
                "uf": sigla_uf,
                "total_gasto": round(total, 2) if total else 0,
                "media_gasto": round(media, 2) if media else 0,
                "quantidade": quantidade,
                "total_deputados": total_deputados
            }
            for sigla_uf, total, media, quantidade, total_deputados in results
        ]

    except Exception as e:
        logger.error(f"Erro ao gerar comparativo: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao processar análise de gastos"
        )  

@analise_router.get("/ranking/alinhamento_resultado")
def get_ranking_alinhamento_partidario(
    year: int = Query(2024, description="Ano de referência para análise", ge=2000),
    
    session: Session = Depends(get_session)
):
    """
    Calcula e ranqueia os partidos pelo seu percentual de alinhamento com o resultado
    final das votações (votar 'Sim' em pautas aprovadas ou 'Não' em reprovadas).
    Entidades: `Partido`, `Deputado`, `VotoIndividual` e `SessaoVotacao`.
    """
    try:
        
        voto_alinhado_expression = case(
            (
                (VotoIndividual.tipo_voto == 'Sim') & (SessaoVotacao.aprovacao == '1'), 1
            ),
            (
                (VotoIndividual.tipo_voto == 'Não') & (SessaoVotacao.aprovacao == '0'), 1
            ),
            else_=0
        )

        stmt = (
            select(
                Partido.sigla,
                Partido.nome_completo,
                func.sum(voto_alinhado_expression).label("votos_alinhados"),
                func.count(VotoIndividual.id).label("votos_totais_decisivos")
            )
            .select_from(Partido)
            .join(Deputado, Partido.id == Deputado.id_partido)
            .join(VotoIndividual, Deputado.id == VotoIndividual.id_deputado)
            .join(SessaoVotacao, VotoIndividual.id_votacao == SessaoVotacao.id)
            .where(VotoIndividual.tipo_voto.in_(['Sim', 'Não']))
            .where(SessaoVotacao.aprovacao.in_(['1', '0']))
            .where(func.cast(VotoIndividual.data_hora_registro, String).startswith(str(year)))
        )

        stmt = stmt.group_by(Partido.sigla, Partido.nome_completo)
        
        resultados = session.exec(stmt).all()
        
        items = []
        for r in resultados:
            if r.votos_totais_decisivos > 0:
                percentual = round((r.votos_alinhados / r.votos_totais_decisivos) * 100, 2)
                items.append({
                    "sigla_partido": r.sigla,
                    "nome_partido": r.nome_completo,
                    "votos_alinhados": r.votos_alinhados,
                    "votos_totais_decisivos": r.votos_totais_decisivos,
                    "percentual_alinhamento": percentual
                })

        items_ordenados = sorted(items, key=lambda p: p['percentual_alinhamento'], reverse=True)

        return items_ordenados
    except Exception as e:
        logger.error(f"Erro ao gerar ranking: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao processar ranking de alinhamento"
        )