from pydantic import BaseModel

class DeputadoRankingDTO(BaseModel):
    id: int
    nome_eleitoral: str
    sigla_partido: str
    sigla_uf: str
    total_votacoes: int
    total_proposicoes: int
