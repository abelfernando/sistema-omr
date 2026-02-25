import json
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

def gerar_folha_respostas(pdf_name, json_name, num_questoes, num_digitos_id, num_alternativas=5):
    try:
        letras = [chr(65 + i) for i in range(num_alternativas)]
        c = canvas.Canvas(pdf_name, pagesize=A4)
        width, height = A4
        
        # Configurações de margens e tamanhos
        margem = 15 * mm
        raio = 2.5 * mm
        tam_ancora = 7 * mm
        margem_seguranca_inferior = 30 * mm # Protege as âncoras inferiores
        
        mapa = {"config": {"num_alternativas": num_alternativas}, "paginas": {}}

        def preparar_pagina(n):
            # 1. Desenhar Âncoras (Essenciais para o OpenCV)
            ancoras = {
                "TL": [margem + tam_ancora/2, height - margem - tam_ancora/2],
                "TR": [width - margem - tam_ancora/2, height - margem - tam_ancora/2],
                "BL": [margem + tam_ancora/2, margem + tam_ancora/2],
                "BR": [width - margem - tam_ancora/2, margem + tam_ancora/2]
            }
            for k, (x, y) in ancoras.items():
                c.rect(x - tam_ancora/2, y - tam_ancora/2, tam_ancora, tam_ancora, fill=1)
            
            # 2. Cabeçalho: Título e Nome
            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(width/2, height - 15*mm, f"FOLHA DE RESPOSTAS - PÁG {n}")
            
            c.setFont("Helvetica", 10)
            c.drawString(margem + 10*mm, height - 25*mm, "NOME:")
            c.rect(margem + 25*mm, height - 27*mm, width - 2*margem - 40*mm, 8*mm)
            
            # 3. Bloco de Identificação (Redundante em cada página)
            y_id = height - 40*mm
            c.setFont("Helvetica-Bold", 10)
            c.drawString(margem + 10*mm, y_id, "IDENTIFICAÇÃO DO ALUNO")
            y_id -= 8*mm
            
            mapa["paginas"][n] = {"ancoras": ancoras, "id_bubbles": [], "questoes": {}}
            
            for i in range(num_digitos_id):
                c.setFont("Helvetica", 8)
                c.drawString(margem + 10*mm, y_id, f"Díg. {i+1}")
                linha_id = []
                for num in range(10):
                    cx, cy = margem + 30*mm + (num * 8*mm), y_id
                    c.circle(cx, cy, raio, stroke=1, fill=0)
                    c.setFont("Helvetica", 7)
                    c.drawCentredString(cx, cy - 1.2*mm, str(num))
                    linha_id.append({"val": num, "x": cx, "y": cy})
                mapa["paginas"][n]["id_bubbles"].append(linha_id)
                y_id -= 8*mm
            
            return y_id - 10*mm # Onde as questões podem começar

        # Configuração Dinâmica de Colunas
        espacamento_opcoes = 7 * mm
        largura_coluna = (num_alternativas * espacamento_opcoes) + 18 * mm
        max_colunas = int((width - 2*margem) // largura_coluna)

        # Estado inicial
        pagina_atual = 1
        y_topo_questoes = preparar_pagina(pagina_atual)
        y_atual = y_topo_questoes
        coluna_atual = 0

        for q in range(1, num_questoes + 1):
            # Checa se o Y atual invadiu a margem de segurança das âncoras
            if y_atual < margem_seguranca_inferior:
                coluna_atual += 1
                y_atual = y_topo_questoes # Reinicia no topo da nova coluna
                
                # Se excedeu as colunas da página, cria nova página
                if coluna_atual >= max_colunas:
                    c.showPage()
                    pagina_atual += 1
                    y_topo_questoes = preparar_pagina(pagina_atual)
                    y_atual = y_topo_questoes
                    coluna_atual = 0

            # 1. Ajuste dinâmico do recuo baseado no número de dígitos
            if q >= 100:
                recuo_texto = 11 * mm  # Aumenta o espaço para 3 dígitos
            else:
                recuo_texto = 8 * mm   # Mantém o padrão para 1 ou 2 dígitos

            # Cálculos de posição
            x_base = margem + 10*mm + (coluna_atual * largura_coluna)
            y_q = y_atual
            
            # Desenha número da questão
            c.setFont("Helvetica-Bold", 9)
            c.drawString(x_base - recuo_texto, y_q, f"{q:02d}:")
            
            # Desenha alternativas
            opts = {}
            for i, letra in enumerate(letras):
                cx, cy = x_base + (i * espacamento_opcoes), y_atual
                c.circle(cx, cy, raio, stroke=1, fill=0)
                c.setFont("Helvetica", 7)
                c.drawCentredString(cx, cy - 1.2*mm, letra)
                opts[letra] = [cx, cy]
            
            mapa["paginas"][pagina_atual]["questoes"][str(q)] = opts
            y_atual -= 8 * mm # Espaçamento entre linhas de questões

        # Finalização
        c.save()
        with open(json_name, "w") as f:
            json.dump(mapa, f, indent=4)
            
        print(f"Arquivos gerados: {pdf_name} e {json_name}")
        print(f"Local: {os.getcwd()}")

        return mapa

    except Exception as e:
        print(f"Erro na geração: {e}")

if __name__ == "__main__":
    # Exemplo: 120 questões, ID de 6 dígitos, 5 alternativas
    gerar_folha_respostas("prova3.pdf", "mapa_prova3.json", 120, 6, num_alternativas=5)