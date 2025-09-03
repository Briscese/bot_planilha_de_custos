import cv2
import pytesseract
import pandas as pd
import re

def extrair_dados_da_imagem(caminho_imagem):
    
    try: 
        imagem = cv2.imread(caminho_imagem)
        if imagem is None:
            print(f"Erro ao carregar a imagem: {caminho_imagem}")
            return None
        imagem_cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
        
        texto_bruto_imagem = pytesseract.image_to_string(imagem_cinza, lang='por')

        if not texto_bruto_imagem.strip():
            print(f"Nenhum texto encontrado na imagem: {caminho_imagem}")
            return None
        return texto_bruto_imagem
    except Exception as e:
        print(f"Erro ao processar a imagem: {e}")
        return None
    
if __name__ == "__main__":
    caminho_imagem = 'pedagios/pedagio1.jpg'
    
    
    texto_extraido = extrair_dados_da_imagem(caminho_imagem)
    
    
    if texto_extraido:
        print("Texto extraído da imagem:")
        print(texto_extraido)
    else:
        print("Falha ao extrair texto da imagem.")