import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

def gerar_folha_final(pdf_name, json_name, num_questoes, num_digitos_id, num_alternativas=5):
    # Define as letras baseadas na quantidade de alternativas (max 26)
    letras = [chr(65 + i) for i in range(num_alternativas)] # A, B, C...
    
    c = canvas.Canvas(pdf_name, pagesize=A4)
    width, height = A4
    margem, raio, tam_ancora = 15*mm, 2.5*mm, 7*mm
    
    mapa = {"config": {"num_alternativas": num_alternativas}, "paginas": {}}

    def preparar_pagina(n):
        # 1. Âncoras
        ancoras = {
            "TL": [margem + tam_ancora/2, height - margem - tam_ancora/2],
            "TR": [width - margem - tam_ancora/2, height - margem - tam_ancora/2],
            "BL": [margem + tam_ancora/2, margem + tam_ancora/2],
            "BR": [width - margem - tam_ancora/2, margem + tam_ancora/2]
        }
        for k, (x, y) in ancoras.items():
            c.rect(x - tam_ancora/2, y - tam_ancora/2, tam_ancora, tam_ancora, fill=1)
        
        # 2. Título e Campo de Nome
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width/2, height - 15*mm, f"FOLHA DE RESPOSTAS - PÁG {n}")
        
        c.setFont("Helvetica", 10)
        c.drawString(margem + 10*mm, height - 25*mm, "NOME:")
        c.rect(margem + 25*mm, height - 27*mm, width - 2*margem - 40*mm, 8*mm)
        
        mapa["paginas"][n] = {"ancoras": ancoras, "id_bubbles": [], "questoes": {}}
        return height - 45*mm # Retorna o Y inicial para o conteúdo

    y_atual = preparar_pagina(1)
    
    # 3. Bloco de Identificação do Aluno (Rótulos Adicionados)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margem + 10*mm, y_atual, "IDENTIFICAÇÃO DO ALUNO")
    y_atual -= 10*mm
    
    for i in range(num_digitos_id):
        c.setFont("Helvetica", 8)
        c.drawString(margem + 10*mm, y_atual, f"Díg. {i+1}")
        linha_id = []
        for num in range(10):
            cx, cy = margem + 30*mm + (num * 8*mm), y_atual
            c.circle(cx, cy, raio, stroke=1, fill=0)
            c.setFont("Helvetica", 7)
            c.drawCentredString(cx, y_atual - 4*mm, str(num))
            linha_id.append({"val": num, "x": cx, "y": cy})
        mapa["paginas"][1]["id_bubbles"].append(linha_id)
        y_atual -= 10*mm

    # 4. Bloco de Questões (Dinâmico)
    y_atual -= 10*mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margem + 10*mm, y_atual, "QUESTÕES")
    y_atual -= 8*mm
    
    for q in range(1, num_questoes + 1):
        # Lógica de nova página se o Y for muito baixo
        if y_atual < 30*mm:
            c.showPage()
            y_atual = preparar_pagina(len(mapa["paginas"]) + 1)
            y_atual -= 40*mm # Ajuste para não sobrepor o cabeçalho na nova página
            
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margem + 10*mm, y_atual, f"{q:02d}:")
        
        opts = {}
        for i, letra in enumerate(letras):
            cx, cy = margem + 25*mm + (i * 10*mm), y_atual
            c.circle(cx, cy, raio, stroke=1, fill=0)
            c.setFont("Helvetica", 8)
            c.drawCentredString(cx, y_atual - 4*mm, letra)
            opts[letra] = [cx, cy]
            
        mapa["paginas"][len(mapa["paginas"])]["questoes"][str(q)] = opts
        y_atual -= 9*mm

    c.save()
    with open(json_name, "w") as f:
        json.dump(mapa, f, indent=4)

# Exemplo de uso: 30 questões, ID de 4 dígitos, e 4 alternativas (A, B, C, D)
gerar_folha_final("folha_corrigida.pdf", "mapa.json", 30, 4, num_alternativas=4)
