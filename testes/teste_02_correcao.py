import requests

BASE_URL = "http://localhost:8000"

def processar_foto(caminho_arquivo):
    print(f"Enviando '{caminho_arquivo}' para processamento...")
    
    try:
        with open(caminho_arquivo, "rb") as img:
            files = {"file": (caminho_arquivo, img, "image/jpeg")}
            # Você pode mudar a nota máxima aqui
            params = {"nota_maxima": 10} 
            
            response = requests.post(
                f"{BASE_URL}/provas/processar-prova/", 
                files=files, 
                params=params
            )

        if response.status_code == 200:
            res = response.json()
            print(f"\n✅ CORREÇÃO CONCLUÍDA")
            print(f"Aluno: {res['aluno']} (Matrícula: {res['matricula']})")
            print(f"Nota: {res['nota']}")
            print(f"Ver correção visual em: {BASE_URL}{res['url_correcao']}")
            
            # Resumo das questões
            acertos = sum(1 for q in res['detalhes'] if q['correto'])
            print(f"Desempenho: {acertos} acertos de {len(res['detalhes'])} questões.")
        else:
            print(f"❌ ERRO NO PROCESSAMENTO: {response.text}")
            
    except FileNotFoundError:
        print(f"❌ ERRO: O arquivo '{caminho_arquivo}' não foi encontrado.")

if __name__ == "__main__":
    # Altere para o nome do arquivo da foto que você tirou
    arquivo_da_foto = "minha_prova_preenchida.jpg" 
    processar_foto(arquivo_da_foto)