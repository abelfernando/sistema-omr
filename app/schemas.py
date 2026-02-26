from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# --- Schemas para Gabarito ---

class GabaritoBase(BaseModel):
    numero_questao: int = Field(..., gt=0, description="O número da questão (1, 2, 3...)")
    resposta_correta: str = Field(..., min_length=1, max_length=1, pattern="^[A-Z]$")

class GabaritoCreate(GabaritoBase):
    pass

class GabaritoOut(GabaritoBase):
    id: int

    class Config:
        from_attributes = True


# --- Schemas para Prova ---

class ProvaBase(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=100, example="Avaliação de Matemática")
    num_questoes: int = Field(..., gt=0, le=200, example=50)
    num_alternativas: int = Field(..., gt=1, le=10, example=5)
    num_digitos_id: int = Field(..., gt=0, le=10, example=6)

class ProvaCreate(ProvaBase):
    # O usuário envia uma lista de respostas corretas ao criar a prova
    gabaritos: List[GabaritoCreate]

class ProvaOut(ProvaBase):
    id: int
    mapa_coordenadas: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True # Permite que o Pydantic leia dados de objetos do SQLAlchemy

class QuestaoDetalhe(BaseModel):
    questao: int
    esperado: str
    recebido: Optional[str]
    correto: bool

class DesempenhoResponse(BaseModel):
    nota: float
    pontuacao_maxima: int
    acertos: int
    total_questoes: int
    detalhe_por_questao: List[QuestaoDetalhe]

class ResultadoResponse(BaseModel):
    id: int
    aluno: str
    matricula: str
    nota: float
    url_correcao: str
    detalhes: List[QuestaoDetalhe]

    class Config:
        from_attributes = True