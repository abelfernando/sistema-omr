# Usa uma imagem Python leve
FROM python:3.13-slim

# Define o diretório de trabalho
WORKDIR /app

# Instala dependências do sistema necessárias para o psycopg2
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Instala o Poetry
RUN pip install poetry

# Copia os arquivos de configuração do Poetry
COPY pyproject.toml poetry.lock* /app/

# Configura o Poetry para não criar ambientes virtuais dentro do contêiner
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi

# Copia o restante do código
COPY . /app

# Comando para rodar a aplicação
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.1", "--port", "8000"]