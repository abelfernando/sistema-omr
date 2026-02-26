import requests
import os

# Como vimos no seu Swagger, a API está respondendo na raiz
BASE_URL = "http://localhost:8000"

def testar_correcao(caminho_imagem):
    # Endpoint correto conforme seu provas.py (@router.post("/processar/upload"))
    # Note que se no main.py não houver prefixo, a URL é /processar/upload
    url_upload = f"{BASE_URL}/processar/upload"
    
    if not os.path.exists(caminho_imagem):
        print(f"❌ ERRO: O arquivo '{caminho_imagem}' não foi encontrado na pasta local.")
        return

    print(f"Enviando '{caminho_imagem}' para correção em {url_upload}...")

    try:
        with open(caminho_imagem, "rb") as img:
            # O nome do campo deve ser 'file' conforme definido no FastAPI: (file: UploadFile = File(...))
            files = {"file": (caminho_imagem, img, "image/jpeg")}
            
            # Parâmetro opcional para definir a faixa de notas (ex: 0 a 10)
            params = {"nota_max": 10}
            
            response = requests.post(url_upload, files=files, params=params)

        if response.status_code == 200:
            res = response.json()
            print("\n✅ CORREÇÃO REALIZADA COM SUCESSO!")
            print(f"ID do Registro: {res.get('id')}")
            print(f"Aluno Identificado: {res.get('aluno')}")
            print(f"Matrícula: {res.get('matricula')}")
            print(f"Nota Final: {res.get('nota_final')}")
            
            print("\n--- Links de Auditoria ---")
            # URLs completas para clicar e ver no navegador
            url_corr = f"{BASE_URL}{res['urls']['correcao']}"
            print(f"Foto com Círculos (Feedback): {url_corr}")
            
            print("\n--- Resumo de Acertos ---")
            print(res.get('acertos'))
            
        elif response.status_code == 404:
            print(f"❌ ERRO 404: Rota não encontrada. Verifique se a URL é {url_upload}")
        else:
            print(f"❌ ERRO {response.status_code}: {response.text}")

    except Exception as e:
        print(f"❌ Falha crítica ao conectar com o servidor: {e}")

if __name__ == "__main__":
    # 1. Gere o PDF com o teste_01
    # 2. Tire uma foto da folha (ou use um mock)
    # 3. Nomeie a foto abaixo:
    NOME_DA_FOTO = "prova_aluno_teste.jpg" 
    testar_correcao(NOME_DA_FOTO)