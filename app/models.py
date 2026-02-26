from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Prova(Base):
    __tablename__ = "provas"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, index=True)
    num_questoes = Column(Integer)
    num_alternativas = Column(Integer, default=5)
    num_digitos_id = Column(Integer, default=6)
    gabarito = Column(JSON) # Armazena {"1": "A", "2": "C", ...}
    mapa_coordenadas = Column(JSON) # Armazena o JSON gerado automaticamente
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    
    #Relacionamento: Uma prova pode ter muitos resultados (coreções)
    resultados = relationship("Resultado", back_populates="prova", cascade="all, delete-orphan")

class Resultado(Base):
    __tablename__ = "resultados"
    
    id = Column(Integer, primary_key=True, index=True)
    # Chave estrangeira ligando ao ID da Prova
    prova_id = Column(Integer, ForeignKey("provas.id", ondelete="CASCADE"), nullable=False)

    # Dados extraídos via OCR/OMR
    aluno_nome = Column(String, index=True)
    aluno_id = Column(String, index=True) # Matrícula preenchida nas bolinhas
    nota = Column(Float)
    
    # Caminhos dos arquivos para visualização no navegador
    arquivo_original = Column(String) # Nome da foto enviada
    arquivo_correcao = Column(String) # Nome da foto com os círculos coloridos
    
    # Armazena o JSON das respostas lidas para conferência futura
    respostas_json = Column(JSON)
    data_processamento = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamento reverso para acessar dados da prova a partir do resultado
    prova = relationship("Prova", back_populates="resultados")
