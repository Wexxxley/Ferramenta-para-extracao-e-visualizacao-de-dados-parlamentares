from typing import Optional
from sqlmodel import Field, SQLModel



class SessaoVotacaoResponse(SQLModel):
    id: Optional[int]
    id_dados_abertos: Optional[str]
    data_hora_registro: Optional[str]
    descricao: Optional[str]
    sigla_orgao: Optional[str]
    aprovacao: Optional[str]
    uri: Optional[str]
    descricao_ultima_abertura_votacao: Optional[str]

    @classmethod
    def from_model(cls, sessao):
        return cls(
            id=sessao.id,
            id_dados_abertos=sessao.id_dados_abertos,
            data_hora_registro=sessao.data_hora_registro,
            descricao=sessao.descricao,
            sigla_orgao=sessao.sigla_orgao,
            aprovacao=sessao.aprovacao,
            uri=sessao.uri,
            descricao_ultima_abertura_votacao=sessao.descricao_ultima_abertura_votacao
        )
