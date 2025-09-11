# app.py


import os
import uuid
import requests
import pandas as pd
import openpyxl
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
from shutil import copyfile
from collections import defaultdict
import re
# --- Importa os "motores" dos outros arquivos ---
from processador_pedagio import extrair_texto_da_imagem, analisar_e_estruturar_texto
from processador_cupom import configurar_detector_wechat, ler_qr_code, extrair_dados_pagina


# Carrega as variáveis de ambiente (senhas) do arquivo .env
load_dotenv()


# --- Configuração Inicial ---
app = Flask(__name__)

# Guardar progresso da coleta de dados iniciais
estado_usuarios = defaultdict(lambda: {"etapa": 0, "dados": {}})

# No PythonAnywhere, os caminhos são relativos ao seu diretório home do usuário
# Ex: /home/seu_usuario_pythonanywhere/
HOME_DIR = os.path.expanduser("~")
# O nome da sua pasta de projeto que você vai criar no PythonAnywhere
PROJECT_FOLDER_NAME = "bot_planilha_de_custos"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

detector_qr = configurar_detector_wechat()

# Carrega as credenciais da Twilio do ambiente
ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")

# --- Configurações da Planilha ---
NOME_DA_ABA = "Plan2"
LINHA_DOS_TOTAIS = 46
ARQUIVO_MODELO = os.path.join(BASE_DIR, "planilha_reembolso_branco.xlsx")
ARQUIVO_DESTINO = os.path.join(BASE_DIR, "reembolso_preenchido.xlsx")

# --- Função Centralizada para Preencher a Planilha ---


def salvar_dados_iniciais(dados, arquivo_modelo, arquivo_destino, nome_da_aba):
    if not os.path.exists(arquivo_destino):
        copyfile(arquivo_modelo, arquivo_destino)

    workbook = openpyxl.load_workbook(arquivo_destino)
    sheet = workbook[nome_da_aba]

    sheet["H3"] = dados.get("nome", "")
    sheet["H4"] = dados.get("cpf_cnpj", "")
    sheet["H5"] = dados.get("banco", "")
    sheet["H6"] = dados.get("agencia_cc", "")
    sheet["H7"] = dados.get("pix", "")
    sheet["F4"] = dados.get("data_inicial", "")
    sheet["F5"] = dados.get("data_final", "")

    workbook.save(arquivo_destino)
    print("✅ Dados iniciais salvos na planilha!")


def preencher_planilha_reembolso(transacoes, arquivo_modelo, arquivo_destino, nome_da_aba, linha_dos_totais):
    if not transacoes:
        print("AVISO: Nenhuma transação para preencher.")
        return
    print(
        f"INFO: Preenchendo {len(transacoes)} transações em '{os.path.basename(arquivo_destino)}'...")
    if not os.path.exists(arquivo_destino):
        copyfile(arquivo_modelo, arquivo_destino)
    try:
        workbook = openpyxl.load_workbook(arquivo_destino)
        sheet = workbook[nome_da_aba]
        linha_atual = 10
        while sheet[f'B{linha_atual}'].value is not None:
            linha_atual += 1

        linhas_necessarias = len(transacoes)
        if (linha_atual + linhas_necessarias) > linha_dos_totais:
            sheet.insert_rows(linha_dos_totais, amount=linhas_necessarias)

        for transacao in transacoes:
            sheet[f'B{linha_atual}'] = transacao.get('Data')
            sheet[f'C{linha_atual}'] = transacao.get('Estabelecimento', '') + (
                ' - ' + transacao.get('Observação', '') if transacao.get('Observação') else '')
            sheet[f'D{linha_atual}'] = transacao.get('Tipo de Despesa')
            sheet[f'F{linha_atual}'] = "São Jose dos Campos"
            sheet[f'G{linha_atual}'] = "São Paulo"
            sheet[f'I{linha_atual}'] = transacao.get('Valor')
            linha_atual += 1
        workbook.save(arquivo_destino)
        print("INFO: Planilha de reembolso atualizada com sucesso!")
    except Exception as e:
        print(f"ERRO CRÍTICO ao preencher a planilha: {e}")


@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    num_media = int(request.values.get("NumMedia", 0))
    resp = MessagingResponse()
    msg = resp.message()

    from_number = request.values.get("From", "")
    texto = request.values.get("Body", "").strip()

    etapas = [
        "Qual o seu nome completo?",
        "Informe o CPF ou CNPJ:",
        "Qual o banco?",
        "Informe Agência e C/C:",
        "Qual a chave PIX?",
        "Data Inicial: (DD/MM/AAAA)",
        "Data Final: (DD/MM/AAAA)"
    ]

    usuario = estado_usuarios[from_number]

    # Se for a primeira vez que o usuário fala, inicia perguntando o nome
    if usuario["etapa"] == 0 and not texto:
        msg.body(etapas[0])
        return str(resp)

    if usuario["etapa"] < len(etapas):
        # Salva a resposta anterior
        if usuario["etapa"] == 0 and texto:
            # Lista de saudações comuns que NÃO devem ser salvas como nome
            saudacoes = ["oi", "olá", "ola", "bom dia",
                         "boa tarde", "boa noite", "hey", "eae"]
            if texto.lower() in saudacoes:
                msg.body("Qual o seu nome completo?")
                return str(resp)
            else:
                usuario["dados"]["nome"] = texto
        elif usuario["etapa"] == 1 and texto:
            usuario["dados"]["cpf_cnpj"] = texto
        elif usuario["etapa"] == 2 and texto:
            usuario["dados"]["banco"] = texto
        elif usuario["etapa"] == 3 and texto:
            usuario["dados"]["agencia_cc"] = texto
        elif usuario["etapa"] == 4 and texto:
            usuario["dados"]["pix"] = texto
        elif usuario["etapa"] == 5 and texto:
            usuario["dados"]["data_inicial"] = texto
        elif usuario["etapa"] == 6 and texto:
            usuario["dados"]["data_final"] = texto


        usuario["etapa"] += 1

        # Se ainda falta perguntar, manda a próxima pergunta
        if usuario["etapa"] < len(etapas):
            msg.body(etapas[usuario["etapa"]])
            return str(resp)
        else:
            # Finalizou todas as perguntas, salva na planilha
            salvar_dados_iniciais(
                usuario["dados"], ARQUIVO_MODELO, ARQUIVO_DESTINO, NOME_DA_ABA)
            msg.body(
                "✅ Dados cadastrados! Agora envie uma imagem do cupom ou pedágio.")
            return str(resp)

    if num_media > 0:
        media_url = request.values.get("MediaUrl0")
        nome_arquivo_temp = os.path.join(TEMP_DIR, f"{uuid.uuid4()}.jpg")

        try:
            # Baixa a imagem com autenticação
            r = requests.get(media_url, auth=(ACCOUNT_SID, AUTH_TOKEN))
            r.raise_for_status()
            with open(nome_arquivo_temp, "wb") as f:
                f.write(r.content)
            print(f"📂 Imagem salva em {os.path.basename(nome_arquivo_temp)}")

            # --- Lógica de Decisão ---
            url_nota = ler_qr_code(detector_qr, nome_arquivo_temp)

            if url_nota:
                print("INFO: QR Code detectado! Processando como Cupom...")
                dados_nota = extrair_dados_pagina(url_nota)
                if dados_nota and dados_nota.get('valor_total', 0) > 0:
                    transacao_cupom = [{
                        "Data": dados_nota['data_emissao'],
                        "Tipo de Despesa": "Combustivel/Alimentação",
                        "Estabelecimento": dados_nota['nome_estabelecimento'],
                        "Valor": dados_nota['valor_total'],
                        "Observação": f"CNPJ: {dados_nota.get('cnpj', 'N/A')}"
                    }]
                    preencher_planilha_reembolso(
                        transacao_cupom, ARQUIVO_MODELO, ARQUIVO_DESTINO, NOME_DA_ABA, LINHA_DOS_TOTAIS)
                    msg.body(
                        f"✅ Cupom de '{dados_nota['nome_estabelecimento']}' (R$ {dados_nota['valor_total']:.2f}) processado!")
                else:
                    msg.body(
                        "❌ QR Code lido, mas falhou ao extrair os dados do site.")
            else:
                print("INFO: Nenhum QR Code. Processando como Pedágio (OCR)...")
                texto_extraido = extrair_texto_da_imagem(nome_arquivo_temp)
                if texto_extraido:
                    lista_transacoes = analisar_e_estruturar_texto(
                        texto_extraido)
                    if lista_transacoes:
                        preencher_planilha_reembolso(
                            lista_transacoes, ARQUIVO_MODELO, ARQUIVO_DESTINO, NOME_DA_ABA, LINHA_DOS_TOTAIS)
                        msg.body(
                            f"✅ Extrato com {len(lista_transacoes)} transações processado!")
                    else:
                        msg.body(
                            "❌ Imagem lida, mas não encontrei transações válidas.")
                else:
                    msg.body("❌ Não consegui ler nenhum texto na imagem.")

        except Exception as e:
            print(f"ERRO GERAL: {e}")
            msg.body("Ocorreu um erro inesperado. 😔 Tente novamente.")
        finally:
            if os.path.exists(nome_arquivo_temp):
                os.remove(nome_arquivo_temp)
    else:
        msg.body(
            "Olá! Por favor, envie uma imagem de um cupom fiscal ou extrato de pedágio.")

    return str(resp)


# O bloco __main__ não é usado no PythonAnywhere, mas é bom para testes locais
if __name__ == "__main__":
    if not all([ACCOUNT_SID, AUTH_TOKEN]):
        print("ERRO FATAL: Configure as variáveis de ambiente TWILIO_ACCOUNT_SID e TWILIO_AUTH_TOKEN no arquivo .env")
    else:
        app.run(port=5000, debug=True)
