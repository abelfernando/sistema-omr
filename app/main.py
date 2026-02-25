from fastapi import FastAPI
from app.database import engine, Base
from app.api.endpoints import provas

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