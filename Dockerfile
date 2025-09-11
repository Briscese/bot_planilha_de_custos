# 1. Usa a imagem oficial do Python 3.12, a mesma do seu ambiente local
FROM python:3.12-slim

# 2. Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# 3. Instala as dependências do sistema operacional de forma mais robusta
# Adiciona 'build-essential' para garantir que as ferramentas de compilação estejam presentes
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    tesseract-ocr \
    tesseract-ocr-por \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 4. Copia o arquivo com a lista de bibliotecas Python para dentro do contêiner
COPY requirements.txt .

# 5. Instala as bibliotecas Python
RUN pip install --no-cache-dir -r requirements.txt

# 6. Instala o navegador que o Playwright precisa
RUN playwright install chromium

# 7. Copia todo o resto do seu projeto para dentro do contêiner
COPY . .

# 8. Expõe a porta que o Render usará para se comunicar com o bot
EXPOSE 10000

# 9. O comando final para iniciar o seu bot com o servidor Gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--timeout", "120"]

