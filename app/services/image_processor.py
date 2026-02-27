import cv2
import numpy as np
from pyzbar import pyzbar
from paddleocr import PaddleOCR

# Inicializa o OCR
ocr_engine = PaddleOCR(use_angle_cls=True, 
                       lang='pt',
                       enable_mkldnn=False                       
                       )

def align_image(image):
    """
    Detecta as âncoras e ordena os pontos corretamente para evitar rotações erradas.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Binarização adaptativa para destacar as âncoras pretas
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 11, 2)
    
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    centros_ancoras = []
    
    for c in cnts:
        area = cv2.contourArea(c)
        if 200 < area < 8000: # Filtro de tamanho para as âncoras
            M = cv2.moments(c)
            if M["m00"] != 0:
                cX = int(M["m10"] / M["m00"])
                cY = int(M["m01"] / M["m00"])
                centros_ancoras.append([cX, cY])

    if len(centros_ancoras) >= 4:
        # Pegamos as 4 maiores áreas detectadas como âncoras
        pts = np.array(centros_ancoras, dtype="float32")
        
        # --- LÓGICA DE ORDENAÇÃO ROBUSTA ---
        rect = np.zeros((4, 2), dtype="float32")
        
        # O ponto superior esquerdo terá a menor soma (x + y)
        # O ponto inferior direito terá a maior soma (x + y)
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        
        # O ponto superior direito terá a menor diferença (y - x)
        # O ponto inferior esquerdo terá a maior diferença (y - x)
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        # Definimos o destino com uma margem interna de 10px para garantir que nada seja cortado
        dst = np.array([
            [10, 10],
            [585, 10],
            [585, 832],
            [10, 832]], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(image, M, (595, 842))
    
    # Se não achar 4 pontos, retorna redimensionado mas sem inverter
    return cv2.resize(image, (595, 842))

def corrigir_orientacao_por_qrcode(image_warped):
    # O pyzbar funciona melhor com um pouco de contraste extra
    gray = cv2.cvtColor(image_warped, cv2.COLOR_BGR2GRAY)
    
    for _ in range(4):
        # Tenta ler no original e em uma versão binarizada (Otsu)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        for img_proc in [gray, thresh]:
            decoded = pyzbar.decode(img_proc)
            if decoded:
                data = decoded[0].data.decode("utf-8")
                if "PROVA_ID:" in data:
                    p_id = int(data.split(":")[-1])
                    return image_warped, p_id
        
        # Rotaciona 90 graus se não achou
        image_warped = cv2.rotate(image_warped, cv2.ROTATE_90_CLOCKWISE)
        gray = cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE)
        
    return image_warped, None

def alinhar_e_identificar(image):
    """
    Pipeline principal: Alinhamento -> Orientação -> Extração.
    """
    # CORRIGIDO: Agora usa a função definida acima
    image_warped = align_image(image) 

    # SALVAR PARA DEBUG (Isso vai aparecer na sua pasta static/processamento)
    debug_path = "static/processamento/debug_ultimo_alinhamento.jpg"
    cv2.imwrite(debug_path, image_warped)
    print(f"DEBUG: Imagem alinhada salva em {debug_path}")
    
    # CORRIGIDO: Agora usa a função de rotação por QR Code
    image_final, prova_id_lido = corrigir_orientacao_por_qrcode(image_warped)
    
    if not prova_id_lido:
        raise ValueError("QR Code de identificação da prova não encontrado ou ilegível.")
    
    return image_final, prova_id_lido

    # dados_aluno_matricula = ler_identificacao_aluno(image_final, mapa_json)
    # respostas = ler_questoes(image_final, mapa_json)
    
    # # Opcional: Ler nome com PaddleOCR
    # nome_aluno = ler_nome_aluno_paddle(image_final)
    
    # return {
    #     "prova_id": prova_id_lido,
    #     "aluno_id": dados_aluno_matricula,
    #     "nome_aluno": nome_aluno,
    #     "respostas": respostas,
    #     "image_processada": image_final
    # }

def ler_identificacao_aluno(image, mapa_json):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
    
    id_detectado = ""
    # Acesse a página 1 (como string, conforme gerado pelo omr_generator)
    bubbles_data = mapa_json['paginas']['1']['id_bubbles']
    
    for coluna in bubbles_data:
        melhor_val = None
        maior_densidade = 0
        
        for bubble in coluna:
            x, y = int(bubble['x']), 842 - int(bubble['y']) # Ajuste de Y invertido
            roi = thresh[y-6:y+6, x-6:x+6]
            densidade = cv2.countNonZero(roi)
            
            if densidade > maior_densidade and densidade > 20:
                maior_densidade = densidade
                melhor_val = bubble['val']
        
        if melhor_val is not None:
            id_detectado += str(melhor_val)
            
    return id_detectado

def ler_nome_aluno_paddle(image_alinhada):
    """
    Extrai o texto manuscrito usando o novo método predict() do PaddleOCR.
    """
    # Recorte da região do nome (ROI) - Ajustado conforme seu layout
    # Se a folha está em 595x842, o campo nome costuma estar entre y=40 e y=120
    roi_nome = image_alinhada[50:150, 50:550] 

    # MODIFICADO: Usando predict() conforme recomendado pela nova versão
    # O predict() retorna uma lista de objetos de predição
    results = ocr_engine.predict(roi_nome)

    if not results:
        return "NOME NAO DETECTADO"

    textos = []
    
    # A estrutura do predict() exige iterar pelos resultados detectados
    for res in results:
        for line in res:
            # line[1][0] contém o texto reconhecido
            # line[1][1] contém a confiança (score)
            textos.append(line[1][0])

    nome_completo = " ".join(textos).strip().upper()
    nome_limpo = nome_completo.replace(" ", "")

    return nome_limpo if nome_limpo else "NOME NAO DETECTADO"

# def ler_nome_aluno_paddle(image_alinhada):
#     # ROI aproximada do retângulo de nome no topo
#     roi_nome = image_alinhada[50:150, 50:500] 
#     result = ocr_engine.ocr(roi_nome)
#     if not result or not result[0]: return "NOME DESCONHECIDO"
#     return " ".join([line[1][0] for line in result[0]]).strip().upper()

def ler_questoes(image_alinhada, mapa_json):
    gray = cv2.cvtColor(image_alinhada, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 11, 2)

    respostas_aluno = {}
    questoes = mapa_json['paginas']['1']['questoes']
    
    for num_q in sorted(questoes.keys(), key=int):
        alternativas = questoes[num_q]
        melhor_alternativa = None
        maior_densidade = 0
        
        for letra, coord in alternativas.items():
            x = int(coord[0])
            y = 842 - int(coord[1]) # Inversão ReportLab -> OpenCV
            
            roi = thresh[y-7:y+7, x-7:x+7]
            densidade = cv2.countNonZero(roi)
            
            if densidade > maior_densidade and densidade > 30: 
                maior_densidade = densidade
                melhor_alternativa = letra
        
        respostas_aluno[int(num_q)] = melhor_alternativa

    return respostas_aluno

def calcular_resultado(respostas_aluno, gabarito_oficial, pontuacao_maxima=100):
    total_questoes = len(gabarito_oficial)
    acertos = 0
    detalhes = []

    for q_num, resp_correta in gabarito_oficial.items():
        resp_aluno = respostas_aluno.get(int(q_num))
        correto = (str(resp_aluno).upper() == str(resp_correta).upper())
        if correto: acertos += 1
        detalhes.append({"questao": q_num, "esperado": resp_correta, "recebido": resp_aluno, "correto": correto})

    nota = (acertos / total_questoes) * pontuacao_maxima if total_questoes > 0 else 0
    return {"nota": round(nota, 2), "acertos": acertos, "total": total_questoes, "detalhes": detalhes}

def gerar_imagem_correcao(image_alinhada, respostas_aluno, gabarito_oficial, mapa_json):
    img_feedback = image_alinhada.copy()
    questoes_map = mapa_json['paginas']['1']['questoes']
    
    for q_num, resp_correta in gabarito_oficial.items():
        q_str = str(q_num)
        if q_str not in questoes_map: continue
        
        resp_aluno = respostas_aluno.get(int(q_num))
        
        # Desenhar correto em VERDE
        c_correto = questoes_map[q_str][resp_correta]
        cv2.circle(img_feedback, (int(c_correto[0]), 842 - int(c_correto[1])), 8, (0, 255, 0), 2)

        # Se errou, desenhar marcação do aluno em VERMELHO
        if resp_aluno and resp_aluno != resp_correta:
            c_aluno = questoes_map[q_str][resp_aluno]
            cv2.circle(img_feedback, (int(c_aluno[0]), 842 - int(c_aluno[1])), 8, (0, 0, 255), 2)
            
    return img_feedback