# Dockerfile
FROM python:3.13.2-slim

# Evita prompts interativos
ENV DEBIAN_FRONTEND=noninteractive

# Instala dependências do sistema
RUN apt-get update && \
    apt-get install -y wget unzip curl gnupg2 && \
    apt-get install -y chromium chromium-driver && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Define diretório de trabalho
WORKDIR /app

# Copia os arquivos para o container
COPY . /app

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Variáveis de ambiente do Chrome
ENV CHROME_BIN="/usr/bin/chromium" \
    CHROMEDRIVER_PATH="/usr/bin/chromedriver"

# Comando padrão
CMD ["python", "main.py"]