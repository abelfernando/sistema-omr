import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.api.endpoints import provas, resultados

# Cria as tabelas no banco de dados automaticamente ao iniciar
# Em projetos maiores, você usaria o Alembic para migrações.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema OMR",
    description="API para Geração e Correção Automática de Provas via QR Code e OMR",
    version="1.0.0"
)

# Configuração de CORS
# Permite que seu frontend (React, Vue ou Mobile) acesse a API sem bloqueios
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicialização de Diretórios Estáticos
# Criamos as pastas necessárias para evitar erros de 'FileNotFound' no upload/geração
for path in ["static/pdfs", "static/processamento"]:
    os.makedirs(path, exist_ok=True)

# Servir Arquivos Estáticos
# Essencial para visualizar a prova corrigida no navegador via URL
app.mount("/static", StaticFiles(directory="static"), name="static")

# 5. Registro de Rotas
# Todos os endpoints (Criar Prova, Listar e Upload de Respostas) estão aqui
app.include_router(provas.router, tags=["Sistema OMR"])

@app.get("/", tags=["Root"])
async def read_root():
    return {
        "status": "online",
        "docs": "/docs"
        }