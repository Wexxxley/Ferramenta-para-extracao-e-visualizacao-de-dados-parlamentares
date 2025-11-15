from typing import Optional, List
from datetime import date, datetime
from sqlalchemy import TEXT, Column
from sqlmodel import Field, SQLModel, Relationship

class SessaoVotacao(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    id_dados_abertos: str = Field(index=True, unique=True, description="ID da votação nos Dados Abertos da Câmara.")
    data_hora_registro: Optional[str] = Field(default=None, description="Data e hora do registro da votação.")
    descricao: Optional[str] = Field(description="Descrição da votação.", sa_column=Column(TEXT))

    sigla_orgao: Optional[str] = Field(default=None, max_length=500)
    aprovacao: Optional[str] = Field(default=None, max_length=500) 
    descricao_ultima_abertura_votacao: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    uri: Optional[str] = Field(default=None, max_length=1000)

    votacoes_proposicao: List["VotacaoProposicao"] = Relationship(back_populates="sessao_votacao")
    votos: List["VotoIndividual"] = Relationship(back_populates="votacao")

