import cv2
import requests
import pandas as pd
import os
from pyz.pyzbar import decode
from bs4 import BeautifulSoup


def ler_qr_code(caminho_imagem):
    print (f"Lendo a imagem: {caminho_imagem}")
    try:
        imagem = cv2.imread(caminho_imagem)
        if imagem is None:
            print(f"Não foi possível ler a imagem: {caminho_imagem}")
            return None
        codigos =  decode(imagem)
        
        if not codigos:
            
            print("Erro: Nenhum QR code encontrado na imagem.")
            
        # Pega o URL do QR code encontrado
        url = codigos[0].data.decode('utf-8')
        print(f"QR code encontrado: {url}")
        return url
    except Exception as e:
        print(f"Erro ao ler o QR code: {e}")
        return None

def extrair_dados_pagina(url):
    print(f"Acessando URL para extrair os dados: {url}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        
        pagina = requests.get(url, headers=headers, timeout=10)
        
        pagina.raise_for_status()  # Verifica se a requisição foi bem-sucedida

        soup = BeautifulSoup(pagina.content, "html.parser")
        
        # Logica da Extração de dados da pagina
        
        nome_estabelecimento = soup.find('div' , id='u20').text.strip()
        
        cnpj = soup.find('div' , id='u28').text.strip()
        
        valor_total = soup.find('span', class_='totalNumb').text.strip().replace(',', '.')
        
        print(f"Nome do Estabelecimento: {nome_estabelecimento}")
        print(f"CNPJ: {cnpj}")
        print(f"Valor Total: {valor_total}")
        
        dados_extraidos = {
            "nome_estabelecimento": nome_estabelecimento,
            "cnpj": cnpj,
            "valor_total": float(valor_total),
            "data_consulta": pd.to_datetime('today').strftime('%Y-%m-%d')
        }
        
        return dados_extraidos
    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar a URL: {e}")
        return None
    except Exception as e:
        print(f"Erro ao extrair dados da página: {e}")
        return None
    
def salvar_em_excel(dados, nome_arquivo="notas_fiscais.xlsx"):
    print(f"Salvando dados no arquivo Excel: {nome_arquivo}")
    
    try 