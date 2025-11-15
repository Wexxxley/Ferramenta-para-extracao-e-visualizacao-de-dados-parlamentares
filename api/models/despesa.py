
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class Despesa(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    id_deputado: int = Field(foreign_key="deputado.id", index=True, description="ID do deputado a quem a despesa pertence.")
    ano: int = Field(description="Ano da despesa.")
    mes: int = Field(description="Mês da despesa.")
    tipo_despesa: Optional[str] = Field(max_length=300, description="Tipo da despesa (ex: 'Passagens Aéreas', 'Combustíveis').")
    valor_liquido: float = Field(description="Valor líquido da despesa.")

    tipo_documento: Optional[str] = Field(default=None, max_length=100)
    url_documento: Optional[str] = Field(default=None, max_length=500)
    nome_fornecedor: Optional[str] = Field(default=None, max_length=255)

    deputado: "Deputado" = Relationship(back_populates="despesas")