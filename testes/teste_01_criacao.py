import requests

# A URL base do seu servidor
BASE_URL = "http://localhost:8000"

def criar_prova():
    payload = {
        "titulo": "Teste Direto na Raiz",
        "num_questoes": 5,
        "num_alternativas": 5,
        "num_digitos_id": 6,
        "gabarito": {
            "1": "A",
            "2": "B",
            "3": "C",
            "4": "D",
            "5": "E"
        }
    }

    # Como vimos no seu Swagger, a rota é apenas "/"
    url_correta = f"{BASE_URL}/"
    
    print(f"Enviando requisição para: {url_correta}")
    
    try:
        response = requests.post(url_correta, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ SUCESSO!")
            print(f"ID da Prova: {data['id']}")
            print(f"PDF gerado em: {BASE_URL}/static/pdfs/prova_{data['id']}.pdf")
        else:
            print(f"❌ ERRO {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"❌ Falha na conexão: {e}")

if __name__ == "__main__":
    criar_prova()