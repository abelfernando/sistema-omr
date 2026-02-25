from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.services.omr_generator import gerar_folha_respostas

router = APIRouter()

@router.post("/provas/", response_model=schemas.ProvaOut)
def criar_prova(prova_in: schemas.ProvaCreate, db: Session = Depends(get_db)):
    # 1. Salva a prova inicial
    db_prova = models.Prova(
        titulo=prova_in.titulo,
        num_questoes=prova_in.num_questoes,
        num_alternativas=prova_in.num_alternativas,
        num_digitos_id=prova_in.num_digitos_id
    )
    db.add(db_prova)
    db.commit()
    db.refresh(db_prova)

    # 2. Gera a folha e obtém o mapa de coordenadas
    pdf_path = f"static/provas/prova_{db_prova.id}.pdf"
    mapa_json = gerar_folha_respostas(
        pdf_path, 
        None, # Não precisamos salvar o arquivo JSON físico se salvarmos no banco
        db_prova.num_questoes, 
        db_prova.num_digitos_id, 
        db_prova.num_alternativas
    )

    # 3. Atualiza a prova com o mapa de coordenadas
    db_prova.mapa_coordenadas = mapa_json
    db.commit()
    
    return db_prova