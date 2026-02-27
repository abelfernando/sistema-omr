import requests
import os

BASE_URL = "http://localhost:8000"

def testar_correcao(caminho_imagem):
    url_upload = f"{BASE_URL}/processar-prova/"
    
    if not os.path.exists(caminho_imagem):
        print(f"❌ ERRO: O arquivo '{caminho_imagem}' não foi encontrado.")
        return

    print(f"Enviando '{caminho_imagem}' para correção em {url_upload}...")

    try:
        with open(caminho_imagem, "rb") as img:
            files = {"file": (caminho_imagem, img, "image/jpeg")}
            params = {"nota_max": 100} # Ajustado para bater com o padrão de nota 100
            
            response = requests.post(url_upload, files=files, params=params)

        if response.status_code == 200:
            res = response.json()
            print("\n" + "="*40)
            print(" ✅ CORREÇÃO REALIZADA COM SUCESSO!")
            print("="*40)
            print(f"ID do Registro: {res.get('id')}")
            print(f"Aluno Identificado: {res.get('aluno_nome')}")
            print(f"Matrícula: {res.get('aluno_id')}")
            print(f"Nota Final: {res.get('nota')}")
            
            print("\n--- 📝 Resumo de Questões ---")
            detalhes = res.get('detalhes', [])
            for item in detalhes:
                status = "✅" if item['correto'] else "❌"
                recebido = item['recebido'] if item['recebido'] else "Em branco"
                print(f"Questão {item['questao']}: Esperado [{item['esperado']}] | Recebido [{recebido}] -> {status}")

            print("\n--- 🔗 Link de Auditoria ---")
            url_servidor = res.get('url_correcao')
            if url_servidor:
                # Correção da chave e tratamento de barras duplicadas
                url_corr = f"{BASE_URL.rstrip('/')}/{res.get('url_correcao').lstrip('/')}"
                print(f"Verificar imagem corrigida em: {url_corr}")
            else:
                print("⚠️  Aviso: O servidor não retornou uma URL de imagem corrigida.")
            print("="*40)
            
        else:
            print(f"❌ ERRO {response.status_code}: {response.text}")

    except Exception as e:
        print(f"❌ Falha crítica no script de teste: {e}")

if __name__ == "__main__":
    NOME_DA_FOTO = r"testes/prova_aluno_teste_3.jpg" 
    testar_correcao(NOME_DA_FOTO)