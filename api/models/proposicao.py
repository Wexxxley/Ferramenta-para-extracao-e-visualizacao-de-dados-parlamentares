from typing import Optional, List
from datetime import date, datetime
from sqlalchemy import TEXT, Column
from sqlmodel import Field, SQLModel, Relationship

class Proposicao(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    id_dados_abertos: str = Field(index=True, unique=True, description="ID da proposição nos Dados Abertos da Câmara.")
    sigla_tipo: str = Field(max_length=10, description="Sigla do tipo de proposição (PL, PEC, MPV, PLP, etc.).")
    ano: int = Field(description="Ano da proposição.")

    ementa: Optional[str] = Field(default=None, description="Ementa (resumo) da proposição.", sa_column=Column(TEXT))
    data_apresentacao: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    url_inteiro_teor: Optional[str] = Field(default=None, max_length=1000)

    # Relações: uma proposição pode estar em várias votações (associativa)
    votacoes_proposicao: List["VotacaoProposicao"] = Relationship(back_populates="proposicao")