import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
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
        db_prova.id,
        db_prova.num_alternativas
    )

    # 3. Atualiza a prova com o mapa de coordenadas
    db_prova.mapa_coordenadas = mapa_json
    db.commit()
    
    return db_prova

@router.get("/provas/{prova_id}/pdf", tags=["Download"])
def baixar_pdf_prova(prova_id: int, db: Session = Depends(get_db)):
    # 1. Busca a prova no banco para verificar a existência
    db_prova = db.query(models.Prova).filter(models.Prova.id == prova_id).first()
    
    if not db_prova:
        raise HTTPException(status_code=404, detail="Prova não encontrada no banco de dados.")

    # 2. Define o caminho do arquivo (certifique-se de que é o mesmo usado na criação)
    # No Docker, os arquivos costumam ficar na pasta de trabalho definida (ex: /app/static/provas/)
    file_path = f"static/provas/prova_{prova_id}.pdf"

    # 3. Verifica se o arquivo físico realmente existe no disco
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Arquivo PDF não encontrado no servidor.")

    # 4. Retorna o arquivo para o navegador
    # media_type='application/pdf' força o tratamento como PDF
    # filename define o nome que aparecerá para o usuário ao salvar
    return FileResponse(
        path=file_path, 
        media_type='application/pdf', 
        filename=f"folha_resposta_{db_prova.titulo.replace(' ', '_')}.pdf"
    )
