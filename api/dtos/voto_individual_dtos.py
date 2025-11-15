
from typing import Optional
from sqlmodel import Field, SQLModel

class VotoIndividualResponse(SQLModel):
    id: Optional[int]
    id_votacao: Optional[int]
    id_deputado: Optional[int]
    tipo_voto: Optional[str]
    data_hora_registro: Optional[str]
    sigla_partido_deputado: Optional[str]
    uri_deputado: Optional[str]
    uri_sessao_votacao: Optional[str]

    @classmethod
    def from_model(cls, voto):
        return cls(
            id=voto.id,
            id_votacao=voto.id_votacao,
            id_deputado=voto.id_deputado,
            tipo_voto=voto.tipo_voto,
            data_hora_registro=voto.data_hora_registro,
            sigla_partido_deputado=voto.sigla_partido_deputado,
            uri_deputado=voto.uri_deputado,
            uri_sessao_votacao=voto.uri_sessao_votacao
        )
