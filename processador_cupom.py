import cv2
import requests
import pandas as pd
import os
from bs4 import BeautifulSoup


# def ler_qr_code(caminho_imagem):
#     print (f"Lendo a imagem: {caminho_imagem}")
#     try:
#         imagem = cv2.imread(caminho_imagem)
#         if imagem is None:
#             print(f"Não foi possível ler a imagem: {caminho_imagem}")
#             return None
#         detector = cv2.QRCodeDetector()
#         dados_decodificados, _, _ = detector.detectAndDecode(imagem)
        
#         if dados_decodificados:
#             print(f"QR Code lido com sucesso: {dados_decodificados}")
#             return dados_decodificados
#         else:
#             print("Erro: Nenhum QR code encontrado na imagem.")
#         return None
#     except Exception as e:
#         print(f"Erro ao ler QR Code: {e}")
#         return None

def extrair_dados_pagina(url):
    print(f"Acessando URL para extrair os dados: {url}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        pagina = requests.get(url, headers=headers, timeout=15)
        pagina.raise_for_status()

        soup = BeautifulSoup(pagina.content, "html.parser")
        
        
        elem_nome = soup.find('div', id='u20')
        nome_estabelecimento = elem_nome.text.strip() if elem_nome else "NOME NÃO ENCONTRADO"
        
        
        cnpj = "CNPJ NÃO ENCONTRADO"
        if elem_nome:
            elem_cnpj = elem_nome.find_next_sibling('div', class_='text')
            if elem_cnpj and "CNPJ:" in elem_cnpj.text:
                
                cnpj = elem_cnpj.text.replace("CNPJ:", "").strip()

        
        valor_texto = "0.0"
        
        label_valor = soup.find(lambda tag: tag.name == 'label' and 'Valor a pagar' in tag.text)
        if label_valor:
            
            span_valor = label_valor.find_next_sibling('span', class_='totalNumb')
            if span_valor:
                valor_texto = span_valor.text.strip().replace(',', '.')
        
        print("--- DADOS EXTRAÍDOS ---")
        print(f"Nome do Estabelecimento: {nome_estabelecimento}")
        print(f"CNPJ: {cnpj}")
        print(f"Valor Total: R$ {valor_texto}")
        
        dados_extraidos = {
            "nome_estabelecimento": nome_estabelecimento,
            "cnpj": cnpj,
            "valor_total": float(valor_texto),
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
    
    try:
        novo_df = pd.DataFrame([dados])
        
        if os.path.exists(nome_arquivo):
            existente_df=pd.read_excel(nome_arquivo)
            final_df = pd.concat([existente_df, novo_df], ignore_index=True)
        else:
            final_df = novo_df

        final_df.to_excel(nome_arquivo, index=False)
        print("Dados salvos com sucesso.")
    except PermissionError:
        print(f"Erro: Permissão negada ao acessar o arquivo {nome_arquivo}.")
    except Exception as e:
        print(f"Erro ao salvar dados no Excel: {e}")


if __name__ == "__main__":

    caminho_imagem = "notas_fiscais/qr_code_teste.jpg"  
    
    url_nota = "https://www.nfce.fazenda.sp.gov.br/NFCeConsultaPublica/Paginas/ConsultaQRCode.aspx?p=35250803031196000170650030001295861733007779|2|1|1|7AB85B08CD66B6B8EF40444BC2ED30D348E2611A"
    
    if url_nota:
        dados_da_nota = extrair_dados_pagina(url_nota)
        
        if dados_da_nota:
            salvar_em_excel(dados_da_nota)
    print("Processamento concluído.")