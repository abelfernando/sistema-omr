# Usa uma imagem Python leve
FROM python:3.13-slim

# Define o diretório de trabalho
WORKDIR /app

# - libpq-dev: para conexão com PostgreSQL
# - gcc: para compilar extensões Python
# - libgl1 e libglib2.0-0: para o OpenCV rodar em ambientes sem interface gráfica
# - libzbar0: biblioteca de sistema para leitura de QR Codes e Códigos de Barras
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    libgl1 \
    libglib2.0-0 \
    libzbar0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Instala o Poetry
RUN pip install poetry

# Copia os arquivos de configuração do Poetry
COPY pyproject.toml poetry.lock* /app/

# Configura o Poetry para não criar ambientes virtuais dentro do contêiner
RUN poetry config virtualenvs.create false && poetry install --no-root --no-interaction --no-ansi

# Copia o restante do código
COPY . /app

# Comando para rodar a aplicação
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]