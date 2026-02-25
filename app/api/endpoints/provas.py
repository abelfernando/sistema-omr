import os
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.services import image_processor
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

# @router.get("/provas/{prova_id}/pdf", tags=["Download"])
# def baixar_pdf_prova(prova_id: int, db: Session = Depends(get_db)):
#     # 1. Busca a prova no banco para verificar a existência
#     db_prova = db.query(models.Prova).filter(models.Prova.id == prova_id).first()
    
#     if not db_prova:
#         raise HTTPException(status_code=404, detail="Prova não encontrada no banco de dados.")

#     # 2. Define o caminho do arquivo (certifique-se de que é o mesmo usado na criação)
#     # No Docker, os arquivos costumam ficar na pasta de trabalho definida (ex: /app/static/provas/)
#     file_path = f"static/provas/prova_{prova_id}.pdf"

#     # 3. Verifica se o arquivo físico realmente existe no disco
#     if not os.path.exists(file_path):
#         raise HTTPException(status_code=404, detail="Arquivo PDF não encontrado no servidor.")

#     # 4. Retorna o arquivo para o navegador
#     # media_type='application/pdf' força o tratamento como PDF
#     # filename define o nome que aparecerá para o usuário ao salvar
#     return FileResponse(
#         path=file_path, 
#         media_type='application/pdf', 
#         filename=f"folha_resposta_{db_prova.titulo.replace(' ', '_')}.pdf"
#     )


# @router.post("/processar/upload")
# async def processar_upload_prova(file: UploadFile = File(...), db: Session = Depends(get_db)):
#     # 1. Converter upload para imagem OpenCV
#     contents = await file.read()
#     nparr = np.frombuffer(contents, np.uint8)
#     image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
#     if image is None:
#         raise HTTPException(status_code=400, detail="Arquivo de imagem inválido.")

#     try:
#         # 2. O pipeline detecta o QR Code e as âncoras para alinhar a imagem 
#         # Retorna o prova_id lido no QR Code e a imagem perfeitamente alinhada
#         image_alinhada, prova_id_lido = image_processor.alinhar_e_identificar(image)
        
#         # 3. Buscar o mapa de coordenadas no banco de dados usando o ID do QR Code 
#         db_prova = db.query(models.Prova).filter(models.Prova.id == prova_id_lido).first()
#         if not db_prova:
#             raise HTTPException(status_code=404, detail=f"Prova ID {prova_id_lido} não encontrada no banco.")

#         # 4. Executar as extrações usando o mapa_coordenadas 
#         mapa = db_prova.mapa_coordenadas
#         nome_aluno = image_processor.ler_nome_aluno_paddle(image_alinhada)
#         id_aluno = image_processor.ler_identificacao_aluno(image_alinhada, mapa)
#         respostas = image_processor.ler_questoes(image_alinhada, mapa)

#         return {
#             "prova_id": prova_id_lido,
#             "aluno_nome": nome_aluno,
#             "aluno_matricula": id_aluno,
#             "respostas": respostas
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Erro no processamento: {str(e)}")
    
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