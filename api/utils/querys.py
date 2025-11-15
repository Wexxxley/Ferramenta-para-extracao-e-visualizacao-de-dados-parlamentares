from sqlmodel import select, func
from api.models.despesa import Despesa

def get_despesas_deputado_2024_subquery():
    
    despesas_subquery = (
        select(
            Despesa.id_deputado,
            func.sum(Despesa.valor_liquido).label("total_despesas")
        )
        .group_by(Despesa.id_deputado)
        .subquery() 
    )
    return despesas_subquery