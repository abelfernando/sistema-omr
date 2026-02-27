import os
import cv2
import uuid
import numpy as np
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.services import image_processor, omr_generator

router = APIRouter()

UPLOAD_DIR = "static/processamento"
PDF_DIR = "static/pdfs"

# Garante que os diretórios existam ao iniciar
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

# --- 1. ENDPOINT PARA CRIAR A PROVA E GERAR PDF ---
@router.post("/", response_model=schemas.ProvaResponse)
def criar_prova(prova_in: schemas.ProvaCreate, db: Session = Depends(get_db)):
    nova_prova = models.Prova(
        titulo=prova_in.titulo,
        num_questoes=prova_in.num_questoes,
        num_alternativas=prova_in.num_alternativas,
        num_digitos_id=prova_in.num_digitos_id,
        gabarito=prova_in.gabarito 
    )
    db.add(nova_prova)
    db.commit()
    db.refresh(nova_prova)

    try:
        pdf_path = f"{PDF_DIR}/prova_{nova_prova.id}.pdf"
        json_debug_path = f"{PDF_DIR}/mapa_prova_{nova_prova.id}.json"

        mapa_gerado = omr_generator.gerar_folha_respostas(
            pdf_name=pdf_path,
            json_name=json_debug_path,
            num_questoes=nova_prova.num_questoes,
            num_digitos_id=nova_prova.num_digitos_id,
            prova_id=nova_prova.id, 
            num_alternativas=nova_prova.num_alternativas
        )

        nova_prova.mapa_coordenadas = mapa_gerado
        db.commit()
        db.refresh(nova_prova)
        return nova_prova

    except Exception as e:
        db.delete(nova_prova)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Erro ao gerar folha OMR: {str(e)}")

# --- 2. ENDPOINT ÚNICO PARA PROCESSAR O UPLOAD E CORREÇÃO ---
@router.post("/processar-prova/", response_model=schemas.ResultadoResponse)
async def upload_prova_omr(
    file: UploadFile = File(...), 
    nota_maxima: int = 100, 
    db: Session = Depends(get_db)
):
    # Validação de Formato
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        raise HTTPException(status_code=400, detail="Envie uma imagem válida (PNG/JPG).")

    # Leitura da Imagem (Bytes para OpenCV)
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img_original = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img_original is None:
        raise HTTPException(status_code=400, detail="Erro ao decodificar a imagem.")

    try:
        # Pipeline de Visão Computacional
        img_alinhada, prova_id_lido = image_processor.alinhar_e_identificar(img_original)

        # Busca dados no banco
        db_prova = db.query(models.Prova).filter(models.Prova.id == prova_id_lido).first()
        if not db_prova:
            raise HTTPException(status_code=404, detail=f"Gabarito ID {prova_id_lido} não encontrado.")

        # OCR e OMR
        mapa = db_prova.mapa_coordenadas
        nome_aluno = image_processor.ler_nome_aluno_paddle(img_alinhada)
        id_aluno = image_processor.ler_identificacao_aluno(img_alinhada, mapa)
        respostas_lidas = image_processor.ler_questoes(img_alinhada, mapa)

        # Cálculo da Nota
        desempenho = image_processor.calcular_resultado(
            respostas_lidas, 
            db_prova.gabarito, 
            pontuacao_maxima=nota_maxima
        )

        # Salvar Imagens de Feedback
        id_operacao = str(uuid.uuid4())
        nome_orig = f"{id_operacao}_orig.jpg"
        nome_corr = f"{id_operacao}_corr.jpg"
        
        cv2.imwrite(os.path.join(UPLOAD_DIR, nome_orig), img_original)
        
        img_feedback = image_processor.gerar_imagem_correcao(
            img_alinhada, respostas_lidas, db_prova.gabarito, mapa
        )
        cv2.imwrite(os.path.join(UPLOAD_DIR, nome_corr), img_feedback)

        # Persistência do Resultado
        novo_res = models.Resultado(
            prova_id=db_prova.id,
            aluno_nome=nome_aluno,
            aluno_id=id_aluno,
            nota=desempenho["nota"],
            arquivo_original=nome_orig,
            arquivo_correcao=nome_corr,
            respostas_json=respostas_lidas
        )
        db.add(novo_res)
        db.commit()
        db.refresh(novo_res)

        # Converte chaves para string e substitui None por String vazia para o Pydantic aceitar
        respostas_formatadas = {str(k): (v if v is not None else "") for k, v in respostas_lidas.items()}

        return {
            "id": novo_res.id,
            "prova_id": db_prova.id,
            "aluno_nome": nome_aluno,
            "aluno_id": id_aluno,
            "nota": desempenho["nota"],
            "arquivo_original": nome_orig,
            "arquivo_correcao": nome_corr, 
            "url_correcao": f"/static/processamento/{nome_corr}" ,          
            "respostas_json": respostas_formatadas,
            "detalhes": desempenho["detalhes"], # Ajustado para o nome da chave no image_processor
            "data_processamento": novo_res.data_processamento if hasattr(novo_res, 'data_processamento') else None 
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")