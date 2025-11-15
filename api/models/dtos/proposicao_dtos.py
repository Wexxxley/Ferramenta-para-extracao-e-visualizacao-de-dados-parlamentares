from typing import Optional
from sqlmodel import Field, SQLModel
from models.proposicao import Proposicao

class ProposicaoResponse(SQLModel):
    id: Optional[int]
    id_dados_abertos: Optional[str]
    sigla_tipo: Optional[str]
    ano: Optional[int]
    ementa: Optional[str]
    data_apresentacao: Optional[str]
    status: Optional[str]
    url_inteiro_teor: Optional[str]

    @classmethod
    def from_model(cls, proposicao: Proposicao):
        return cls(
            id=proposicao.id,
            id_dados_abertos=proposicao.id_dados_abertos,
            sigla_tipo=proposicao.sigla_tipo,
            ano=proposicao.ano,
            ementa=proposicao.ementa,
            data_apresentacao=proposicao.data_apresentacao,
            status=proposicao.status,
            url_inteiro_teor=proposicao.url_inteiro_teor
        )
    
class ProposicaoMaisVotadaDTO(SQLModel):
    id: int
    id_dados_abertos: str
    sigla_tipo: str
    ano: int
    ementa: Optional[str]
    total_votacoes: int
