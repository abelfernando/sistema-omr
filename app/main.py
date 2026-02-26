import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base
from app.api.endpoints import provas

# Define o caminho para a pasta de processamento
# Certifique-se de que este caminho seja o mesmo usado no seu service de upload
UPLOAD_DIR = "static/processamento"

# Cria o diretório caso ele não exista para evitar erro na inicialização
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

# Monta a rota estática
# directory: pasta física no servidor
# html: False para servir apenas arquivos brutos (imagens/pdfs)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Cria a pasta de PDFs se não existir
os.makedirs("static/provas", exist_ok=True)

# Cria as tabelas no banco de dados automaticamente ao iniciar
# Em projetos maiores, você usaria o Alembic para migrações.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema OMR API",
    description="Backend para geração e processamento de folhas de respostas (OMR)",
    version="1.0.0"
)

# Inclui as rotas do módulo de provas
app.include_router(provas.router, prefix="/api", tags=["Provas"])

@app.get("/")
def read_root():
    return {"message": "Bem-vindo à API do Sistema OMR. Acesse /docs para a documentação."}