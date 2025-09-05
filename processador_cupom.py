# processador_cupom.py (Versão final só com reembolso)

import cv2
import os
import re
import requests
import openpyxl
from bs4 import BeautifulSoup
from shutil import copyfile
from playwright.sync_api import sync_playwright

# --- CONFIGURAÇÃO DO DETECTOR WECHAT (usa pasta local) ---
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

# --- LER QR CODE ---
def ler_qr_code(detector, caminho_imagem):
    imagem = cv2.imread(caminho_imagem)
    if imagem is None:
        raise FileNotFoundError(f"Imagem não encontrada: {caminho_imagem}")

    codigos, _ = detector.detectAndDecode(imagem)
    return codigos[0] if codigos else None

# --- EXTRAIR DADOS DO CUPOM ---
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
        
        nome_estabelecimento = "NÃO ENCONTRADO"
        cnpj = "NÃO ENCONTRADO"
        valor_texto = "0.0"
        data_emissao = "NÃO ENCONTRADA"

        # Nome
        nome_elem = soup.select_one('div.txtTopo')
        if nome_elem:
            nome_estabelecimento = nome_elem.text.strip()

        # CNPJ
        cnpj_div = soup.find(lambda tag: tag.name == 'div' and 'CNPJ:' in tag.text)
        if cnpj_div:
            cnpj_match = re.search(r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', cnpj_div.text)
            if cnpj_match:
                cnpj = cnpj_match.group(1)

        # Valor Total
        label_valor = soup.find('label', string=re.compile(r'Valor a pagar', re.IGNORECASE))
        if label_valor:
            valor_span = label_valor.find_next_sibling('span', class_='totalNumb')
            if valor_span:
                valor_texto = valor_span.text.strip().replace(',', '.')

        # Data de emissão
        strong_emissao = soup.find('strong', string=re.compile(r'Emissão', re.IGNORECASE))
        if strong_emissao:
            texto_completo = strong_emissao.parent.get_text(" ", strip=True)
            match_data = re.search(r'(\d{2}/\d{2}/\d{4})', texto_completo)
            if match_data:
                data_emissao = match_data.group(1)

        valor_float = float(valor_texto) if valor_texto else 0.0

        print("\n--- DADOS EXTRAÍDOS ---")
        print(f"Estabelecimento: {nome_estabelecimento}")
        print(f"CNPJ: {cnpj}")
        print(f"Valor Total: R$ {valor_texto}")
        print(f"Data de Emissão: {data_emissao}")

        return {
            "data_emissao": data_emissao,
            "nome_estabelecimento": nome_estabelecimento,
            "cnpj": cnpj,
            "valor_total": valor_float
        }
    except Exception as e:
        print(f"ERRO ao extrair dados da página: {e}")
        return None

# --- PREENCHER PLANILHA DE REEMBOLSO ---
def preencher_planilha_reembolso(transacoes, arquivo_modelo, arquivo_destino, nome_da_aba, linha_dos_totais):
    if not transacoes:
        print("AVISO: Nenhuma transação para preencher.")
        return

    print(f"INFO: Preenchendo {len(transacoes)} transações em '{arquivo_destino}'...")

    if not os.path.exists(arquivo_destino):
        copyfile(arquivo_modelo, arquivo_destino)
    
    try:
        workbook = openpyxl.load_workbook(arquivo_destino)
        sheet = workbook[nome_da_aba]

        linha_atual = 10
        while sheet[f'B{linha_atual}'].value is not None:
            linha_atual += 1
        
        print(f"INFO: Inserindo dados a partir da linha {linha_atual}.")

        linhas_necessarias = len(transacoes)
        espaco_disponivel = linha_dos_totais - linha_atual
        if linhas_necessarias > espaco_disponivel:
            linhas_para_inserir = linhas_necessarias - espaco_disponivel
            sheet.insert_rows(linha_dos_totais, amount=linhas_para_inserir)

        for transacao in transacoes:
            sheet[f'B{linha_atual}'] = transacao['Data']
            sheet[f'C{linha_atual}'] = transacao['Estabelecimento']
            sheet[f'D{linha_atual}'] = transacao['Tipo de Despesa']
            sheet[f'F{linha_atual}'] = "São Paulo"
            sheet[f'G{linha_atual}'] = "São Paulo"
            sheet[f'I{linha_atual}'] = transacao['Valor']
            
            linha_atual += 1

        workbook.save(arquivo_destino)
        print("INFO: Planilha de reembolso atualizada com sucesso!")
    except Exception as e:
        print(f"ERRO CRÍTICO ao preencher a planilha: {e}")

# --- EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    detector_qr = configurar_detector_wechat()
    pasta_de_imagens = "notas_fiscais"

    ARQUIVO_MODELO = "planilha_reembolso_branco.xlsx"
    ARQUIVO_DESTINO = "reembolso_preenchido.xlsx"
    NOME_DA_ABA = "Plan2"
    LINHA_DOS_TOTAIS = 46

    imagens_para_processar = [
        os.path.join(pasta_de_imagens, f)
        for f in os.listdir(pasta_de_imagens)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ]

    todas_as_transacoes_mapeadas = []

    for caminho_imagem in imagens_para_processar:
        url_nota = ler_qr_code(detector_qr, caminho_imagem)
        if url_nota:
            dados_da_nota = extrair_dados_pagina(url_nota)
            if dados_da_nota and dados_da_nota.get('valor_total', 0) > 0:
                transacao_mapeada = {
                    "Data": dados_da_nota['data_emissao'],
                    "Tipo de Despesa": "Combustivel/Alimentação",
                    "Estabelecimento": dados_da_nota['nome_estabelecimento'],
                    "Valor": dados_da_nota['valor_total'],
                }
                todas_as_transacoes_mapeadas.append(transacao_mapeada)

    if todas_as_transacoes_mapeadas:
        preencher_planilha_reembolso(
            todas_as_transacoes_mapeadas,
            ARQUIVO_MODELO,
            ARQUIVO_DESTINO,
            NOME_DA_ABA,
            LINHA_DOS_TOTAIS
        )

    print("\nProcessamento concluído.")
