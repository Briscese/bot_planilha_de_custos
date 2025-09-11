# 1. Comece com uma imagem oficial do Python 3.11 (leve e otimizada)
FROM python:3.11-slim

# 2. Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# 3. Instala as dependências do sistema operacional (Tesseract) ANTES de tudo
#    --no-install-recommends economiza espaço
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

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
