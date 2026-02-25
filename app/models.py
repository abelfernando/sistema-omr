from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .database import Base

class Prova(Base):
    __tablename__ = "provas"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, index=True)
    num_questoes = Column(Integer)
    num_alternativas = Column(Integer)
    num_digitos_id = Column(Integer)
    mapa_coordenadas = Column(JSON) # Armazena o JSON gerado automaticamente

    gabaritos = relationship("Gabarito", back_populates="prova")

class Gabarito(Base):
    __tablename__ = "gabaritos"

    id = Column(Integer, primary_key=True, index=True)
    prova_id = Column(Integer, ForeignKey("provas.id"))
    numero_questao = Column(Integer)
    resposta_correta = Column(String(1))

    prova = relationship("Prova", back_populates="gabaritos")