from sqlmodel import SQLModel
from typing import Optional

class DespesaResponse(SQLModel):
    id: int
    id_deputado: int
    ano: int
    mes: int
    tipo_despesa: str
    valor_liquido: float
    tipo_documento: Optional[str] = None
    url_documento: Optional[str] = None
    nome_fornecedor: Optional[str] = None
