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