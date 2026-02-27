import cv2
import numpy as np
from pyzbar import pyzbar
from paddleocr import PaddleOCR

# Inicializa o OCR
ocr_engine = PaddleOCR(use_angle_cls=True, 
                       lang='pt',
                       enable_mkldnn=False                       
                       )

# Configurações para A4 em 300 DPI
DPI = 300
LARGURA_A4 = 2480  # 210mm
ALTURA_A4 = 3508   # 297mm

# Margem de 30 pontos do ReportLab convertida para 300 DPI
# (30 / 72) * 300 = 125 pixels
MARGEM_PX = 125

# Coordenadas de DESTINO fixas (Onde as âncoras DEVERIAM estar)
DEST_TL = [MARGEM_PX, MARGEM_PX]
DEST_TR = [LARGURA_A4 - MARGEM_PX, MARGEM_PX]
DEST_BL = [MARGEM_PX, ALTURA_A4 - MARGEM_PX]
DEST_BR = [LARGURA_A4 - MARGEM_PX, ALTURA_A4 - MARGEM_PX]

# Constantes de Conversão
DPI_TARGET = 300
DPI_REPORTLAB = 72
ESCALA = DPI_TARGET / DPI_REPORTLAB  # 4.1666...
LARGURA_A4_PX = 2480
ALTURA_A4_PX = 3508

def converter_coordenada(ponto_x, ponto_y):
    """
    Converte coordenadas do JSON (points) para Pixels (300 DPI)
    ajustando a inversão do eixo Y.
    """
    px = int(ponto_x * ESCALA)
    # Inverte o Y: Altura total menos a posição vinda do ReportLab
    py = int(ALTURA_A4_PX - (ponto_y * ESCALA))
    return px, py

def align_image(image):
    # 1. Pré-processamento para encontrar os quadrados pretos
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 11, 2)

    # 2. Detectar contornos das âncoras
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    anchors = []
    
    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        
        # Filtra por formas quadrangulares e tamanho mínimo
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            aspect_ratio = float(w) / h
            if 0.8 <= aspect_ratio <= 1.2 and w > 20: # Ajuste o tamanho conforme necessário
                M = cv2.moments(cnt)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    anchors.append([cx, cy])

    if len(anchors) < 4:
        raise ValueError(f"Foram encontradas apenas {len(anchors)} âncoras. Necessário 4.")

    # 3. Ordenar as âncoras detectadas (Top-Left, Top-Right, Bottom-Left, Bottom-Right)
    # Lógica: soma (x+y) mínima é TL, máxima é BR. Diferença (x-y) máxima é TR, mínima é BL.
    pts = np.array(anchors, dtype="float32")
    rect = np.zeros((4, 2), dtype="float32")
    
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)] # TL
    rect[3] = pts[np.argmax(s)] # BR
    
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)] # TR
    rect[2] = pts[np.argmax(diff)] # BL

    # 4. Definir pontos de DESTINO REAIS baseados no template
    dst = np.array([
        DEST_TL,
        DEST_TR,
        DEST_BL,
        DEST_BR
    ], dtype="float32")

    # 5. Calcular Matriz de Homografia e Aplicar Warp
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (LARGURA_A4, ALTURA_A4), flags=cv2.INTER_CUBIC)

    return warped

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
    # Fator de escala: converte Pontos (72 DPI) para Pixels (300 DPI)
    escala = 300 / 72
    altura_px = 3508

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Substituindo threshold fixo por Adaptive para melhor performance com fotos de celular
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 11, 2)
    
    id_detectado = ""
    # Acesse a página 1
    bubbles_data = mapa_json['paginas']['1']['id_bubbles']
    
    for coluna in bubbles_data:
        melhor_val = None
        maior_densidade = 0
        
        for bubble in coluna:
            # APLICAÇÃO DA ESCALA E INVERSÃO DE EIXO
            x = int(bubble['x'] * escala)
            y = int(altura_px - (bubble['y'] * escala))
            
            # ROI ajustado: em 300 DPI, o raio de 6 pixels era muito pequeno. 
            # Subimos para 20 pixels para cobrir a bolinha da matrícula.
            raio = 20 
            roi = thresh[y-raio:y+raio, x-raio:x+raio]
            densidade = cv2.countNonZero(roi)
            
            # Threshold de densidade aumentado para compensar a área maior do ROI
            if densidade > maior_densidade and densidade > 300:
                maior_densidade = densidade
                melhor_val = bubble['val']
        
        if melhor_val is not None:
            id_detectado += str(melhor_val)
            
    return id_detectado

def ler_nome_aluno_paddle(image_alinhada):
    """
    Extrai o texto manuscrito usando o novo método predict() do PaddleOCR,
    ajustado para a resolução de 300 DPI.
    """
    # Fator de escala: converte Pontos (72 DPI) para Pixels (300 DPI)
    escala = 300 / 72  # ~4.1667

    # Ajuste do ROI (Região de Interesse)
    # Se no layout original (595x842) o nome estava em y:50-150 e x:50-550
    # Multiplicamos esses limites pela escala para encontrar a posição na imagem de 300 DPI.
    y1, y2 = int(50 * escala), int(150 * escala)
    x1, x2 = int(50 * escala), int(550 * escala)
    
    # Recorte da região do nome (ROI) na nova escala (aprox. 208:625, 208:2291)
    roi_nome = image_alinhada[y1:y2, x1:x2] 

    # Chamada do OCR
    results = ocr_engine.predict(roi_nome)

    if not results:
        return "NOME NAO DETECTADO"

    textos = []
    
    # Iteração pelos resultados do predict()
    for res in results:
        for line in res:
            # line[1][0] contém o texto reconhecido
            textos.append(line[1][0])

    # Join e limpeza profunda de espaços
    nome_completo = "".join(textos).strip().upper()
    nome_limpo = nome_completo.replace(" ", "")

    return nome_limpo if nome_limpo else "NOME NAO DETECTADO"

# def ler_nome_aluno_paddle(image_alinhada):
#     # ROI aproximada do retângulo de nome no topo
#     roi_nome = image_alinhada[50:150, 50:500] 
#     result = ocr_engine.ocr(roi_nome)
#     if not result or not result[0]: return "NOME DESCONHECIDO"
#     return " ".join([line[1][0] for line in result[0]]).strip().upper()

def ler_questoes(image_alinhada, mapa_json):
    # Fator de escala: converte Pontos (72 DPI) para Pixels (300 DPI)
    escala = 300 / 72  # Aproximadamente 4.1667
    altura_px = 3508   # Altura da nossa imagem normalizada

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
            # APLICAÇÃO DA ESCALA E INVERSÃO PRECISA
            # Multiplicamos a coordenada original pela escala e subtraímos da altura total em pixels
            x = int(coord[0] * escala)
            y = int(altura_px - (coord[1] * escala))
            
            # ROI aumentado: como a imagem agora é maior (300 DPI), 
            # o raio de 7 pixels ficou pequeno. Aumentamos para ~25 pixels.
            raio = 25 
            roi = thresh[y-raio:y+raio, x-raio:x+raio]
            densidade = cv2.countNonZero(roi)
            
            # O limite de densidade (30) também precisa subir proporcionalmente à área
            # Uma bolinha preenchida em 300 DPI terá muito mais pixels que em 72 DPI.
            if densidade > maior_densidade and densidade > 400: 
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

def gerar_imagem_correcao(image_alinhada, respostas_lidas, gabarito, mapa_json):
    """
    Desenha círculos verdes (acerto) e vermelhos (erro) na imagem de 300 DPI,
    usando um raio dinâmico para máxima precisão.
    """
    # Fator de escala e altura para 300 DPI
    escala = 300 / 72
    altura_px = 3508
    
    # Criar uma cópia para não alterar a imagem original e converter para BGR para cores
    img_feedback = image_alinhada.copy()
    
    # Pre-processamento para detecção dinâmica (Otsu Thresholding)
    gray = cv2.cvtColor(img_feedback, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    questoes_mapa = mapa_json['paginas']['1']['questoes']

    for num_q, alternativas in questoes_mapa.items():
        correta = gabarito.get(str(num_q))
        lida = respostas_lidas.get(int(num_q))

        for letra, coord in alternativas.items():
            # CONVERSÃO PARA 300 DPI
            cx = int(coord[0] * escala)
            cy = int(altura_px - (coord[1] * escala))
            
            # --- AJUSTE DINÂMICO DE RAIO ---
            # Define um ROI local maior para busca
            raio_busca = 50 
            # Garante que o ROI não saia da imagem
            y1 = max(0, cy - raio_busca)
            y2 = min(altura_px, cy + raio_busca)
            x1 = max(0, cx - raio_busca)
            x2 = min(2480, cx + raio_busca)
            
            roi_local = thresh[y1:y2, x1:x2]
            
            # Encontra contornos no ROI
            cnts, _ = cv2.findContours(roi_local, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            raio_dinamico = 30 # Raio padrão caso a busca falhe
            
            if cnts:
                # Pega o maior contorno no ROI (que deve ser a bolinha)
                c_max = max(cnts, key=cv2.contourArea)
                
                # Encontra o círculo delimitador mínimo (minEnclosingCircle)
                # que dá o raio real da bolinha na imagem normalizada
                (_, _), radio_encontrado = cv2.minEnclosingCircle(c_max)
                
                # Adiciona uma margem de segurança ao raio (ex: +20%) para o desenho
                raio_dinamico = int(radio_encontrado * 1.20)
                
                # Garante um raio mínimo de desenho
                if raio_dinamico < 25:
                    raio_dinamico = 30
            
            # --- LÓGICA DE CORES E DESENHO ---
            cor = None
            if letra == correta:
                cor = (0, 255, 0)  # Verde (BGR)
            elif letra == lida and lida != correta:
                cor = (0, 0, 255)  # Vermelho (BGR)

            if cor:
                # Espessura dinâmica baseada no raio para manter proporção
                espessura = max(2, int(raio_dinamico / 10))
                cv2.circle(img_feedback, (cx, cy), raio_dinamico, cor, espessura)
                
                # Se for o erro do aluno, adiciona um círculo preenchido menor (marcador)
                if cor == (0, 0, 255):
                    cv2.circle(img_feedback, (cx, cy), 10, cor, -1)

    return img_feedback
