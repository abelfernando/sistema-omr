import requests

BASE_URL = "http://localhost:8000"

def criar_prova():
    payload = {
        "titulo": "Prova de Python e OMR",
        "num_questoes": 10,
        "num_alternativas": 5,
        "num_digitos_id": 4,
        "gabarito": {
            "1": "A", "2": "B", "3": "C", "4": "D", "5": "E",
            "6": "A", "7": "B", "8": "C", "9": "D", "10": "E"
        }
    }

    print("Enviando requisição de criação...")
    response = requests.post(f"{BASE_URL}/provas/", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ SUCESSO!")
        print(f"ID da Prova: {data['id']}")
        print(f"Título: {data['titulo']}")
        print(f"URL do PDF: {BASE_URL}/static/pdfs/prova_{data['id']}.pdf")
        print("\nPróximo passo: Abra o PDF, imprima ou exiba na tela, "
              "preencha e tire uma foto para o próximo teste.")
    else:
        print(f"❌ ERRO: {response.text}")

if __name__ == "__main__":
    criar_prova()