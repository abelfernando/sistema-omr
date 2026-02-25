import cv2
import numpy as np
from pyzbar import pyzbar
from paddleocr import PaddleOCR

# Inicializa o OCR apenas uma vez (fora da função) para carregar o modelo na memória
# use_angle_cls=True ajuda a identificar se o texto está levemente inclinado
ocr_engine = PaddleOCR(use_angle_cls=True, lang='pt', show_log=False)

def processar_prova_completa(image_bruta, mapa_json):
    """
    Pipeline principal: Alinhamento -> Orientação -> Extração.
    """
    # 1. Alinhamento inicial pelas âncoras (Warp Perspective)
    # Usa Adaptive Threshold internamente para lidar com iluminação de celular
    image_warped = align_image(image_bruta) 
    
    # 2. Correção de Orientação e Leitura do ID da Prova
    # Garante que a folha não está de ponta-cabeça
    image_final, prova_id_lido = corrigir_orientacao_por_qrcode(image_warped)
    
    if not prova_id_lido:
        raise ValueError("QR Code de identificação da prova não encontrado ou ilegível.")

    # 3. Extração de Dados (ID do Aluno e Respostas)
    # Agora que a imagem está 100% alinhada com o mapa_json
    dados_aluno = ler_identificacao_aluno(image_final, mapa_json)
    respostas = ler_questoes(image_final, mapa_json)
    
    return {
        "prova_id": prova_id_lido,
        "aluno_id": dados_aluno,
        "respostas": respostas
    }

def ler_identificacao_aluno(image, mapa_json):
    """
    Percorre as coordenadas das bolinhas de identificação do aluno.
    """
    id_detectado = ""
    # O mapa_json['paginas']['1']['id_bubbles'] contém as listas de coordenadas 
    for coluna in mapa_json['paginas']['1']['id_bubbles']:
        melhor_val = None
        maior_densidade = 0
        
        for bubble in coluna:
            # bubble['x'], bubble['y'], bubble['val'] 
            # Extrai uma pequena região (ROI) ao redor da coordenada
            x, y = int(bubble['x']), int(bubble['y'])
            roi = image[y-5:y+5, x-5:x+5] # Ajustar área conforme necessário
            
            # Calcula densidade de pixels pretos (marcação)
            densidade = np.sum(roi == 0) 
            if densidade > maior_densidade:
                maior_densidade = densidade
                melhor_val = bubble['val']
        
        if melhor_val is not None:
            id_detectado += str(melhor_val)
            
    return id_detectado


def ler_nome_aluno_paddle(image_alinhada):
    """
    Extrai o texto manuscrito do campo NOME usando PaddleOCR.
    """
    # Coordenadas baseadas no seu layout (A4: 595x842)
    # Margem + 25mm até o fim do retângulo
    y1, y2 = 105, 140  # Faixa vertical do retângulo de nome
    x1, x2 = 85, 530   # Faixa horizontal
    
    # Recorta a região do nome (ROI)
    roi_nome = image_alinhada[y1:y2, x1:x2]

    # O PaddleOCR aceita o array do OpenCV diretamente
    result = ocr_engine.ocr(roi_nome, cls=True)

    # O resultado é uma lista de listas. Vamos extrair apenas o texto.
    if not result or not result[0]:
        return "NOME NAO DETECTADO"

    textos = [line[1][0] for line in result[0]]
    nome_completo = " ".join(textos).strip().upper()

    return nome_completo

def ler_questoes(image_alinhada, mapa_json):
    """
    Analisa a marcação das questões baseando-se nas coordenadas do mapa.
    """
    # 1. Pré-processamento: Converter para Tons de Cinza e Threshold Adaptativo
    # Isso transforma a marcação (caneta azul/preta) em preto puro (0)
    gray = cv2.cvtColor(image_alinhada, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 11, 2
    )

    respostas_aluno = {}
    
    # O mapa pode ter múltiplas páginas. Vamos iterar por elas.
    # No seu modelo, o mapa tem a chave 'paginas' 
    paginas = mapa_json.get("paginas", {})
    
    for num_pag, dados_pag in paginas.items():
        questoes = dados_pag.get("questoes", {})
        
        # Ordenamos as questões numericamente
        for num_q in sorted(questoes.keys(), key=int):
            alternativas = questoes[num_q]
            melhor_alternativa = None
            maior_densidade = 0
            
            # Analisamos cada letra (A, B, C, D, E) 
            for letra, coord in alternativas.items():
                # Coordenadas vindas do JSON (ReportLab usa Y invertido em relação ao OpenCV)
                x = int(coord[0])
                # Ajuste de Y: No seu omr_generator, o ReportLab conta de baixo para cima 
                # A imagem alinhada (842px de altura) precisa da inversão:
                y = 842 - int(coord[1])
                
                # Definimos o raio de busca (ex: 5 pixels ao redor do centro)
                raio = 6
                roi = thresh[y-raio:y+raio, x-raio:x+raio]
                
                # Contamos pixels brancos (que eram pretos na imagem original devido ao THRESH_BINARY_INV)
                densidade = cv2.countNonZero(roi)
                
                # Critério de marcação: densidade mínima para evitar sujeira/ruído
                if densidade > maior_densidade and densidade > 25: 
                    maior_densidade = densidade
                    melhor_alternativa = letra
            
            respostas_aluno[int(num_q)] = melhor_alternativa

    return respostas_aluno


def alinhar_e_identificar(image):
    # Detecta as âncoras e faz o warp inicial para A4 (595x842) 
    image_warped = align_image(image) 
    
    # Busca o QR Code na imagem alinhada
    decoded_objects = pyzbar.decode(image_warped)
    if not decoded_objects:
        # Se não achou, tenta rotacionar a imagem em passos de 90º (bússola) 
        for _ in range(3):
            image_warped = cv2.rotate(image_warped, cv2.ROTATE_90_CLOCKWISE)
            decoded_objects = pyzbar.decode(image_warped)
            if decoded_objects: break
            
    if not decoded_objects:
        raise ValueError("QR Code não encontrado. Certifique-se de que o cabeçalho está visível.")

    # Extrai o ID da prova (ex: "PROVA_ID:15") 
    data = decoded_objects[0].data.decode("utf-8")
    prova_id = int(data.split(":")[-1])
    
    return image_warped, prova_id


def calcular_resultado(respostas_aluno, gabarito_oficial, pontuacao_maxima=100):
    """
    Compara as respostas e calcula o desempenho baseado em uma faixa de notas customizável.
    
    :param respostas_aluno: Dict com as respostas lidas do OMR {id_questao: "LETRA"}
    :param gabarito_oficial: Dict com o gabarito do banco {id_questao: "LETRA"}
    :param pontuacao_maxima: Valor da nota máxima (Default: 100)
    """
    total_questoes = len(gabarito_oficial)
    acertos = 0
    detalhes = []

    # Itera sobre o gabarito oficial para conferência
    for q_num, resposta_correta in gabarito_oficial.items():
        # Garante que a chave da questão seja tratada como inteiro para bater com o OMR
        q_int = int(q_num)
        resposta_aluno = respostas_aluno.get(q_int)
        
        is_correto = (str(resposta_aluno).upper() == str(resposta_correta).upper())
        if is_correto:
            acertos += 1
            
        detalhes.append({
            "questao": q_int,
            "esperado": resposta_correta,
            "recebido": resposta_aluno,
            "correto": is_correto
        })

    # Cálculo da nota proporcional à faixa definida
    if total_questoes > 0:
        nota_final = (acertos / total_questoes) * pontuacao_maxima
    else:
        nota_final = 0
    
    return {
        "nota": round(nota_final, 2),
        "pontuacao_maxima": pontuacao_maxima,
        "acertos": acertos,
        "total_questoes": total_questoes,
        "detalhe_por_questao": detalhes
    }
