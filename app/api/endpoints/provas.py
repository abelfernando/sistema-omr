import os
import cv2
import uuid
import numpy as np
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.services import image_processor
from app.services.omr_generator import gerar_folha_respostas

router = APIRouter()

@router.post("/", response_model=schemas.ProvaResponse)
def criar_prova(prova_in: schemas.ProvaCreate, db: Session = Depends(get_db)):
    # 1. Cria o objeto inicial no banco para obter o ID (necessário para o QR Code)
    nova_prova = models.Prova(
        titulo=prova_in.titulo,
        num_questoes=prova_in.num_questoes,
        num_alternativas=prova_in.num_alternativas,
        num_digitos_id=prova_in.num_digitos_id,
        gabarito=prova_in.gabarito # Salva o Dict diretamente no campo JSON 
    )
    db.add(nova_prova)
    db.commit()
    db.refresh(nova_prova)

    try:
        # 2. Gerar o PDF e o Mapa de Coordenadas
        # Definimos caminhos para salvar o arquivo físico temporário ou final
        pdf_path = f"static/pdfs/prova_{nova_prova.id}.pdf"
        os.makedirs("static/pdfs", exist_ok=True)

        # Chamamos seu serviço enviando o prova_id para o QR Code 
        mapa_gerado = omr_generator.gerar_folha_respostas(
            pdf_name=pdf_path,
            num_questoes=nova_prova.num_questoes,
            num_digitos_id=nova_prova.num_digitos_id,
            prova_id=nova_prova.id, # O ID que acabou de ser gerado 
            num_alternativas=nova_prova.num_alternativas
        )

        # 3. Atualiza a prova com o mapa de coordenadas gerado
        nova_prova.mapa_coordenadas = mapa_gerado
        db.commit()
        db.refresh(nova_prova)

    except Exception as e:
        # Se falhar a geração do PDF, removemos o registro para não poluir o banco
        db.delete(nova_prova)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Erro ao gerar folha OMR: {str(e)}")

    return nova_prova

    
 
@router.post("/processar/upload")
async def processar_upload_prova(file: UploadFile = File(...), 
                                 nota_max: int= 100, # Parâmetro opcional na URL ou Body
                                 db: Session = Depends(get_db)):
    try:
        # 1. Alinhamento e Identificação automática via QR Code
        image_alinhada, prova_id_lido = image_processor.alinhar_e_identificar(image)
        
        # 2. Busca os dados da prova (Gabarito e Mapa) no banco
        db_prova = db.query(models.Prova).filter(models.Prova.id == prova_id_lido).first()
        if not db_prova:
            raise HTTPException(status_code=404, detail="Prova não cadastrada.")

        # 3. Extração OMR e OCR (Nome, Matrícula, Respostas)
        mapa = db_prova.mapa_coordenadas
        nome_aluno = image_processor.ler_nome_aluno_paddle(image_alinhada)
        id_aluno = image_processor.ler_identificacao_aluno(image_alinhada, mapa)
        respostas_lidas = image_processor.ler_questoes(image_alinhada, mapa)

        # 4. Cálculo do Resultado
        resultado = calcular_resultado(respostas_lidas, db_prova.gabarito)

        # 5. (Opcional) Salvar o resultado no banco de dados aqui
        novo_resultado = models.Resultado(
            prova_id=db_prova.id,
            aluno_nome=nome_aluno,
            aluno_id=id_aluno,
            nota=resultado["nota"],
            respostas_json=respostas_lidas
        )
        db.add(novo_resultado)
        db.commit()

        return {
            "status": "sucesso",
            "aluno": nome_aluno,
            "matricula": id_aluno,
            "desempenho": resultado
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

UPLOAD_DIR = "static/processamento"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/processar/upload")
async def processar_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # ... (lógica de alinhamento e leitura OMR/OCR já implementada) ...
    
    # 1. Gerar nomes únicos para os arquivos
    id_unico = str(uuid.uuid4())
    nome_orig = f"{id_unico}_orig.jpg"
    nome_corr = f"{id_unico}_corr.jpg"
    
    path_orig = os.path.join(UPLOAD_DIR, nome_orig)
    path_corr = os.path.join(UPLOAD_DIR, nome_corr)

    # 2. Salvar a foto original (imagem binária vinda do upload)
    with open(path_orig, "wb") as buffer:
        buffer.write(await file.read())

    # 3. Gerar e salvar a imagem de correção
    img_corrigida_visual = gerar_imagem_correcao(
        image_alinhada, respostas_lidas, db_prova.gabarito, mapa
    )
    cv2.imwrite(path_corr, img_corrigida_visual)

    # 4. Salvar no banco com os nomes dos arquivos
    novo_resultado = models.Resultado(
        prova_id=db_prova.id,
        aluno_nome=nome_aluno,
        aluno_id=id_aluno,
        nota=resultado["nota"],
        arquivo_original=nome_orig,
        arquivo_correcao=nome_corr,
        respostas_json=respostas_lidas
    )
    db.add(novo_resultado)
    db.commit()

    return {
        "mensagem": "Correção concluída",
        "nota": resultado["nota"],
        "url_correcao": f"/static/processamento/{nome_corr}"
    }

# app/api/endpoints/provas.py

@router.post("/processar-prova/", response_model=schemas.ResultadoResponse)
async def upload_prova_omr(
    file: UploadFile = File(...), 
    nota_maxima: int = 100, 
    db: Session = Depends(get_db)
):
    # 1. Validação de Formato
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        raise HTTPException(status_code=400, detail="Envie uma imagem válida (PNG/JPG).")

    # 2. Leitura da Imagem
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img_original = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    try:
        # 3. Pipeline de Visão Computacional
        # Alinha a folha e lê o prova_id via QR Code
        img_alinhada, prova_id_lido = image_processor.alinhar_e_identificar(img_original)

        # 4. Recuperação dos Dados da Prova no Banco
        db_prova = db.query(models.Prova).filter(models.Prova.id == prova_id_lido).first()
        if not db_prova:
            raise HTTPException(status_code=404, detail="Gabarito não encontrado para esta prova.")

        # 5. Processamento OCR (PaddleOCR) e OMR (Bolhas)
        nome_aluno = image_processor.ler_nome_aluno_paddle(img_alinhada)
        id_aluno = image_processor.ler_identificacao_aluno(img_alinhada, db_prova.mapa_coordenadas)
        respostas_lidas = image_processor.ler_questoes(img_alinhada, db_prova.mapa_coordenadas)

        # 6. Conferência e Nota
        desempenho = image_processor.calcular_resultado(
            respostas_lidas, 
            db_prova.gabarito, 
            pontuacao_maxima=nota_maxima
        )

        # 7. Salvar Imagens e Registro de Resultado
        id_operacao = str(uuid.uuid4())
        nome_orig = f"{id_operacao}_orig.jpg"
        nome_corr = f"{id_operacao}_corr.jpg"
        
        # Salva as imagens no diretório estático configurado no main.py
        cv2.imwrite(os.path.join(UPLOAD_DIR, nome_orig), img_original)
        
        img_feedback = image_processor.gerar_imagem_correcao(
            img_alinhada, respostas_lidas, db_prova.gabarito, db_prova.mapa_coordenadas
        )
        cv2.imwrite(os.path.join(UPLOAD_DIR, nome_corr), img_feedback)

        # Persistência no PostgreSQL
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

        return {
            "id": novo_res.id,
            "aluno": nome_aluno,
            "matricula": id_aluno,
            "nota": desempenho["nota"],
            "url_correcao": f"/static/processamento/{nome_corr}",
            "detalhes": desempenho["detalhe_por_questao"]
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")