from sqlmodel import SQLModel
from typing import Optional

class DeputadoRankingDespesa(SQLModel):
    id: int
    id_dados_abertos: int
    nome_eleitoral: Optional[str]
    sigla_partido: Optional[str]
    sigla_uf: Optional[str]
    url_foto: Optional[str]
    sexo: Optional[str]
    total_despesas: Optional[float]

class PartidoRankingDespesa(SQLModel):
    id: int
    id_dados_abertos: int
    sigla: str
    nome_completo: str
    total_despesas: float

class ResumoDeputado(SQLModel):
    id: int
    sessoes_votadas: int
    total_gasto_2024: float
