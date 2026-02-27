FROM python:3.13-slim

WORKDIR /app

# Instalação de dependências do sistema
# libzbar0: Leitura de QR Code
# libgl1/libglib2.0-0: OpenCV
# libgomp1: Essencial para o PaddlePaddle rodar modelos de IA
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

# Configura Poetry e instala dependências
COPY pyproject.toml poetry.lock* /app/
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

COPY . /app

# Variavel de ambiente para mitigar erros do Paddle no Docker
ENV FLAGS_enable_pir_api=0
ENV PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]