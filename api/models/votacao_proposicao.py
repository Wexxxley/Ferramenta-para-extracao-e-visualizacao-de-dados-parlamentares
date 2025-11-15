from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class VotacaoProposicao(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    id_proposicao: int = Field(foreign_key="proposicao.id", index=True, description="ID da proposição associada.")
    id_votacao: int = Field(foreign_key="sessaovotacao.id", index=True, description="ID da sessão de votação associada.")

    proposicao: "Proposicao" = Relationship(back_populates="votacoes_proposicao")
    sessao_votacao: "SessaoVotacao" = Relationship(back_populates="votacoes_proposicao")