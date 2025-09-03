from flask import Flask, request

from processador_cupom import ler_qr_code, salvar_em_excel, extrair_dados_pagina
from processador_pedagio import extrair_texto_da_imagem, analisar_e_estruturar_texto, salvar_em_excel

app = Flask(__name__)

@app.route('/whatsapp', methods=['POST'])
def webhook_whatsapp():
    data = request.json
    # Processar o dado recebido
    return {"status": "success"}

if __name__ == '__main__':
    app.run(port=5000, debug=True)
    


