import os
import uuid
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

load_dotenv()


# --- Importa os dois motores ---
from processador_cupom import (
    configurar_detector_wechat,
    ler_qr_code,
    extrair_dados_pagina,
    preencher_planilha_reembolso as salvar_cupom,
)
from processador_pedagio import (
    extrair_texto_da_imagem,
    analisar_e_estruturar_texto,
    preencher_planilha_reembolso as salvar_pedagio,
)

app = Flask(__name__)

# --- Configura o detector do WeChat ---
detector = configurar_detector_wechat()

# --- Variáveis de ambiente ---
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")


@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    print("📩 Recebido webhook do WhatsApp")

    dados_recebidos = request.form.to_dict()
    print(f"📑 Dados recebidos: {dados_recebidos}")

    media_url = request.values.get("MediaUrl0", None)
    num_media = int(request.values.get("NumMedia", 0))

    resp = MessagingResponse()
    msg = resp.message()

    if num_media > 0:
        print(f"🖼️ Recebida uma imagem: {media_url}")

        try:
            file_path = baixar_imagem(media_url, "entrada")

            # 1️⃣ Tenta ler QRCode (cupom)
            dados_qr = ler_qr_code(detector, file_path)
            if dados_qr:
                dados_da_nota = extrair_dados_pagina(dados_qr)
                salvar_cupom(
                    [
                        {
                            "Data": dados_da_nota["data_emissao"],
                            "Tipo de Despesa": "Combustivel/Alimentação",
                            "Estabelecimento": dados_da_nota["nome_estabelecimento"],
                            "Valor": dados_da_nota["valor_total"],
                        }
                    ],
                    "planilha_reembolso_branco.xlsx",
                    "reembolso_preenchido.xlsx",
                    "Plan2",
                    46,
                )
                msg.body(
                    f"✅ Cupom processado: {dados_da_nota['nome_estabelecimento']} - R${dados_da_nota['valor_total']}"
                )
                return str(resp)

            # 2️⃣ Se não tem QRCode, tenta OCR (pedágio)
            texto_extraido = extrair_texto_da_imagem(file_path)
            lista_transacoes = analisar_e_estruturar_texto(texto_extraido)

            if lista_transacoes:
                salvar_pedagio(
                    lista_transacoes,
                    "planilha_reembolso_branco.xlsx",
                    "reembolso_preenchido.xlsx",
                    "Plan2",
                    46,
                )
                msg.body(
                    f"✅ Pedágio processado: {len(lista_transacoes)} lançamentos adicionados."
                )
                return str(resp)

            # 3️⃣ Caso não reconheça nada
            msg.body("❌ Não consegui identificar se é cupom ou pedágio.")

        except Exception as e:
            msg.body(f"⚠️ Erro ao processar imagem: {str(e)}")

    else:
        remetente = request.values.get("From", "")
        texto = request.values.get("Body", "").strip()
        print(f"💬 Recebido texto de {remetente}: {texto}")
        msg.body("Por favor envie uma nota fiscal (cupom) ou comprovante de pedágio.")

    return str(resp)



def baixar_imagem(media_url, prefixo):
    """Baixa a imagem recebida via WhatsApp e salva em disco"""
    extensao = os.path.splitext(media_url)[1] or ".jpg"
    file_name = f"{prefixo}_{uuid.uuid4().hex}{extensao}"
    file_path = os.path.join("downloads", file_name)

    os.makedirs("downloads", exist_ok=True)

    resp = requests.get(media_url, auth=(ACCOUNT_SID, AUTH_TOKEN))  # <- adiciona auth
    resp.raise_for_status()  # opcional, vai lançar exceção se falhar
    with open(file_path, "wb") as f:
        f.write(resp.content)

    print(f"📂 Imagem salva em {file_path}")
    return file_path



if __name__ == "__main__":
    if not all([ACCOUNT_SID, AUTH_TOKEN]):
        print(
            "ERRO FATAL: Configure as variáveis de ambiente TWILIO_ACCOUNT_SID e TWILIO_AUTH_TOKEN."
        )
    else:
        app.run(host="0.0.0.0", port=5000, debug=True)
