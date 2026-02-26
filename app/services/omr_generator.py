import json
import os
import qrcode
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

def gerar_folha_respostas(pdf_name, num_questoes, num_digitos_id, prova_id, num_alternativas=5):
    """
    Gera o PDF da folha de respostas e retorna o mapa de coordenadas dos círculos.
    """
    c = canvas.Canvas(pdf_name, pagesize=A4)
    width, height = A4 # 595.27 x 841.89 pts
    
    mapa_coordenadas = {
        "paginas": {
            "1": {
                "questoes": {},
                "id_bubbles": []
            }
        }
    }

    # 1. Desenhar Âncoras (4 quadrados pretos nos cantos)
    # Margem de 15mm, tamanho de 7mm
    margem = 15 * mm
    tamanho_ancora = 7 * mm
    
    # Bottom-Left, Top-Left, Top-Right, Bottom-Right
    pos_ancoras = [
        (margem, margem), 
        (margem, height - margem - tamanho_ancora),
        (width - margem - tamanho_ancora, height - margem - tamanho_ancora),
        (width - margem, margem)
    ]
    
    for x, y in pos_ancoras:
        c.rect(x, y, tamanho_ancora, tamanho_ancora, fill=1)

    # 2. Gerar QR Code com o ID da Prova
    # Formato: "PROVA_ID:123"
    qr_data = f"PROVA_ID:{prova_id}"
    qr = qrcode.make(qr_data)
    qr_path = f"temp_qr_{prova_id}.png"
    qr.save(qr_path)
    
    # Posicionar QR Code no topo direito
    c.drawInlineImage(qr_path, width - 45*mm, height - 45*mm, width=30*mm, height=30*mm)
    os.remove(qr_path) # Limpa o arquivo temporário

    # 3. Gerar Campo de Nome (Retângulo para OCR)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margem + 10*mm, height - 35*mm, "NOME:")
    c.rect(margem + 28*mm, height - 38*mm, 100*mm, 10*mm) # Retângulo do Nome

    # 4. Gerar Bolinhas de Identificação (Matrícula)
    # Aqui você deve iterar para criar as colunas de 0-9
    x_id = margem + 10*mm
    y_id_start = height - 60*mm
    for col in range(num_digitos_id):
        coluna_coords = []
        for num in range(10):
            x = x_id + (col * 7*mm)
            y = y_id_start - (num * 7*mm)
            c.circle(x, y, 2.5*mm, stroke=1, fill=0)
            c.setFont("Helvetica", 6)
            c.drawCentredString(x, y - 1*mm, str(num))
            # Salva coordenada central para o OMR
            coluna_coords.append({"x": x, "y": y, "val": num})
        mapa_coordenadas["paginas"]["1"]["id_bubbles"].append(coluna_coords)

    # 5. Gerar Bolinhas das Questões
    y_q_start = y_id_start - 80*mm
    letras = ["A", "B", "C", "D", "E"][:num_alternativas]
    
    for q in range(1, num_questoes + 1):
        y_q = y_q_start - (q * 8*mm)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margem + 5*mm, y_q - 1*mm, f"{q:02d}:")
        
        coords_q = {}
        for i, letra in enumerate(letras):
            x_q = margem + 20*mm + (i * 10*mm)
            c.circle(x_q, y_q, 3*mm, stroke=1, fill=0)
            c.setFont("Helvetica", 7)
            c.drawCentredString(x_q, y_q - 1*mm, letra)
            # Salva no mapa (x, y)
            coords_q[letra] = [x_q, y_q]
        
        mapa_coordenadas["paginas"]["1"]["questoes"][str(q)] = coords_q

    c.save()
    return mapa_coordenadas
