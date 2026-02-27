from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Schemas para Prova ---

class ProvaBase(BaseModel):
    titulo: str
    num_questoes: int
    num_alternativas: int = 5
    num_digitos_id: int = 6
    gabarito: Dict[str, str] # Ex: {"1": "A", "2": "C"}

class ProvaCreate(ProvaBase):
    mapa_coordenadas: Optional[Dict] = None # Gerado internamente ou enviado no setup

class ProvaResponse(ProvaBase):
    id: int
    data_criacao: datetime
    
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
    prova_id: int
    aluno_nome: str
    aluno_id: str
    nota: float
    #URLs para o frontend exibir as imagens
    arquivo_original: Optional[str]
    arquivo_correcao: Optional[str]
    url_correcao: Optional[str] = None
    respostas_json: Dict[str, str]
    detalhes: Optional[List[QuestaoDetalhe]] = None # Campo calculado na API
    data_processamento: datetime

    class Config:
        from_attributes = True