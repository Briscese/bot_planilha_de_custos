import os
import uuid
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse


from processador_cupom import configurar_detector_wechat, ler_qr_code, extrair_dados_pagina, salvar_em_excel as salvar_cupom
from processador_pedagio import extrair_texto_da_imagem, analisar_e_estruturar_texto, salvar_em_excel as salvar_pedagio


app = Flask(__name__)
detector_qr = configurar_detector_wechat()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# Carrega as credenciais da Twilio do ambiente
ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")

@app.route('/whatsapp', methods=['POST'])
def webhook_whatsapp():
    dados_recebidos = request.form
    num_media = int(dados_recebidos.get('NumMedia', 0))
    response = MessagingResponse()
    
    if num_media > 0:
        url_da_imagem = dados_recebidos.get('MediaUrl0')
        nome_arquivo_temp = os.path.join(TEMP_DIR, f'{uuid.uuid4()}.jpg')
        
        try:
            # Baixa a imagem de forma autenticada
            conteudo_imagem = requests.get(url_da_imagem, auth=(ACCOUNT_SID, AUTH_TOKEN)).content
            with open(nome_arquivo_temp, 'wb') as f:
                f.write(conteudo_imagem)

            # LÓGICA DE DECISÃO
            url_nota = ler_qr_code(detector_qr, nome_arquivo_temp)

            if url_nota:
                dados_da_nota = extrair_dados_pagina(url_nota)
                if dados_da_nota and dados_da_nota.get('valor_total', 0) > 0:
                    salvar_cupom(dados_da_nota)
                    response.message(f"✅ Nota Fiscal de '{dados_da_nota['nome_estabelecimento']}' (R$ {dados_da_nota['valor_total']:.2f}) processada!")
                else:
                    response.message("❌ QR Code lido, mas falha ao extrair dados do site.")
            else:
                texto_extraido = extrair_texto_da_imagem(nome_arquivo_temp)
                if texto_extraido:
                    lista_de_transacoes = analisar_e_estruturar_texto(texto_extraido)
                    if lista_de_transacoes:
                        salvar_pedagio(lista_de_transacoes)
                        response.message(f"✅ Extrato com {len(lista_de_transacoes)} transações processado!")
                    else:
                        response.message("❌ Imagem lida, mas não encontrei transações válidas.")
                else:
                    response.message("❌ Não consegui ler nenhum texto na imagem.")
        
        except Exception as e:
            print(f"ERRO GERAL: {e}")
            response.message("Ocorreu um erro inesperado. 😔")
        finally:
            if os.path.exists(nome_arquivo_temp):
                os.remove(nome_arquivo_temp)
    else:
        response.message("Olá! Envie a imagem de um cupom fiscal ou extrato de pedágio.")

    return str(response)

if __name__ == '__main__':
    if not all([ACCOUNT_SID, AUTH_TOKEN]):
        print("ERRO FATAL: Configure as variáveis de ambiente TWILIO_ACCOUNT_SID e TWILIO_AUTH_TOKEN.")
    else:
        app.run(port=5000, debug=True)