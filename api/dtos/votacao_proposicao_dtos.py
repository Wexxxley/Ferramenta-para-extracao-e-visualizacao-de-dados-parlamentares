from typing import Optional
from sqlmodel import Field, SQLModel

class VotacaoProposicaoResponse(SQLModel):
    id: Optional[int]
    id_proposicao: Optional[int]
    id_votacao: Optional[int]

    @classmethod
    def from_model(cls, vp):
        return cls(
            id=vp.id,
            id_proposicao=vp.id_proposicao,
            id_votacao=vp.id_votacao
        )
