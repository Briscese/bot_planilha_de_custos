from flask import Flask, request
import requests

from processador_cupom import ler_qr_code, salvar_em_excel, extrair_dados_pagina
from processador_pedagio import extrair_texto_da_imagem, analisar_e_estruturar_texto, salvar_em_excel

app = Flask(__name__)

@app.route('/whatsapp', methods=['POST'])
def webhook_whatsapp():
    
    print("Recebido webhook do WhatsApp")
    dados_recebidos = request.form
    print(f"Dados recebidos: {dados_recebidos}")
    
    num_media = int(dados_recebidos.get('NumMedia', 0))
    
    mensagem_retorno = "Obrigado pela Mensagem!!!"
    
    # Verificar se o que recebeu é uma imagem ou texto
    if num_media > 0:
        # Isso é uma imagem
        url_imagem = dados_recebidos.get('MediaUrl0')
        tipo_imagem = dados_recebidos.get('MediaContentType0')
        print (f"Recebido uma imagem do tipo: {tipo_imagem} - URL: {url_imagem}")
        
        mensagem_retorno = "Imagem recebida com sucesso!"
    
    else:
        # Isso é um texto
        texto_recebido = dados_recebidos.get('Body')
        remetente = dados_recebidos.get('From')
        print(f"Recebido um texto de {remetente}: {texto_recebido}")
        mensagem_retorno = "Por favor enviar uma nota fiscal ou imagem de pedágio."
    
    return mensagem_retorno, 200



if __name__ == '__main__':
    app.run(port=5000, debug=True)
    


