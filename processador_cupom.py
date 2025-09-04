import cv2
import pandas as pd
import os
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def configurar_detector_wechat():
    print("INFO: Configurando o detector de QR Code avançado (WeChat)...")
    model_dir = "wechat_qr_models"
    model_files = [
        os.path.join(model_dir, "detect.prototxt"), os.path.join(model_dir, "detect.caffemodel"),
        os.path.join(model_dir, "sr.prototxt"), os.path.join(model_dir, "sr.caffemodel")
    ]
    if not all(os.path.exists(f) for f in model_files):
        print(f"ERRO FATAL: Arquivos de modelo não encontrados na pasta '{model_dir}'.")
        return None
    try:
        print("INFO: Modelos encontrados. Inicializando detector...")
        return cv2.wechat_qrcode_WeChatQRCode(*model_files)
    except Exception as e:
        print(f"ERRO FATAL: Não foi possível inicializar o detector. Erro: {e}")
        return None

def ler_qr_code(detector, caminho_imagem):
    print(f"\nINFO: Lendo a imagem com WeChat QR Detector: {caminho_imagem}")
    try:
        imagem = cv2.imread(caminho_imagem)
        if imagem is None: return None
        urls_encontradas, _ = detector.detectAndDecode(imagem)
        if not urls_encontradas:
            print("ERRO: Nenhum QR Code foi encontrado.")
            return None
        url = urls_encontradas[0].strip()
        print(f"INFO: QR Code lido com sucesso!")
        return url
    except Exception as e:
        print(f"ERRO: Ocorreu um erro ao ler o QR Code: {e}")
        return None

def extrair_dados_pagina(url):
    print(f"Acessando URL: {url}")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            html_content = page.content()
            browser.close()

        soup = BeautifulSoup(html_content, "html.parser")
        
        # Lógica de extração baseada no seu código funcional
        nome_elem = soup.find('div', id='u20')
        nome_estabelecimento = nome_elem.text.strip() if nome_elem else "NÃO ENCONTRADO"
        
        cnpj = "NÃO ENCONTRADO"
        # A busca pelo CNPJ é mais robusta procurando pela div que contém o texto
        cnpj_div = soup.find(lambda tag: tag.name == 'div' and 'CNPJ:' in tag.text)
        if cnpj_div:
            cnpj_match = re.search(r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', cnpj_div.text)
            if cnpj_match:
                cnpj = cnpj_match.group(1)
        
        valor_texto = "0.0"
        # A busca pela label "Valor a pagar" é a mais confiável
        label_valor = soup.find('label', string=re.compile(r'Valor a pagar', re.IGNORECASE))
        if label_valor:
            valor_span = label_valor.find_next_sibling('span', class_='totalNumb')
            if valor_span:
                valor_texto = valor_span.text.strip().replace(',', '.')
        
        print("\n--- DADOS EXTRAÍDOS ---")
        print(f"Estabelecimento: {nome_estabelecimento}")
        print(f"CNPJ: {cnpj}")
        print(f"Valor Total: R$ {valor_texto}")
        
        valor_float = float(valor_texto) if valor_texto else 0.0

        return {"nome_estabelecimento": nome_estabelecimento, "cnpj": cnpj, "valor_total": valor_float, "data_consulta": pd.to_datetime('today', utc=True).strftime('%Y-%m-%d')}
    except Exception as e:
        print(f"ERRO ao extrair dados da página: {e}")
        return None
    
def salvar_em_excel(dados, nome_arquivo="notas_fiscais.xlsx"):
    print(f"Salvando dados no arquivo Excel: {nome_arquivo}")
    try:
        novo_df = pd.DataFrame([dados])
        if os.path.exists(nome_arquivo):
            existente_df = pd.read_excel(nome_arquivo)
            final_df = pd.concat([existente_df, novo_df], ignore_index=True)
        else:
            final_df = novo_df
        final_df.drop_duplicates(inplace=True)
        final_df.to_excel(nome_arquivo, index=False)
        print("Dados salvos com sucesso.")
    except Exception as e:
        print(f"Erro ao salvar dados no Excel: {e}")

if __name__ == "__main__":
    detector_qr = configurar_detector_wechat()
    if detector_qr:
        pasta_de_imagens = "notas_fiscais"
        imagens_para_processar = [os.path.join(pasta_de_imagens, f) for f in os.listdir(pasta_de_imagens) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        print(f"INFO: {len(imagens_para_processar)} imagens encontradas na pasta '{pasta_de_imagens}'.")
        
        for caminho_imagem in imagens_para_processar:
            url_nota = ler_qr_code(detector_qr, caminho_imagem)
            if url_nota:
                dados_da_nota = extrair_dados_pagina(url_nota)
                if dados_da_nota:
                    salvar_em_excel(dados_da_nota)
    
    print("\nProcessamento concluído.")