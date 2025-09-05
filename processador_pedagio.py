import cv2
import pytesseract
import pandas as pd
import re
import os
import locale
from shutil import copyfile
import openpyxl

try:
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except Exception as e:
    print(f"AVISO de configuração: {e}")

def extrair_texto_da_imagem(caminho_imagem):
    print(f"\nINFO: Lendo a imagem com OCR: {caminho_imagem}")
    try:
        imagem = cv2.imread(caminho_imagem)
        if imagem is None:
            return None
        imagem_cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
        texto_bruto = pytesseract.image_to_string(imagem_cinza, lang='por')
        return texto_bruto if texto_bruto.strip() else None
    except Exception as e:
        print(f"ERRO durante o OCR: {e}")
        return None

# --- Função de análise (mantida) ---
def analisar_e_estruturar_texto(texto_bruto):
    print("INFO: Analisando com a lógica de pareamento por ordem (a que funciona)...")
    transacoes_finais = []
    
    linhas = texto_bruto.strip().split('\n')
    
    regex_data = re.compile(r"(\d{1,2} de \w+)")
    regex_valor = re.compile(r"R\$\s*(\d+[,.]?\d*)")
    regex_identificador = re.compile(r"(\d{3})\s*-?\s*([A-Z0-9]{7})")
    regex_descricao = re.compile(r"(Passagem|Estacionamento)", re.IGNORECASE)

    datas = [{'linha': i, 'data': m.group(1).strip()} for i, l in enumerate(linhas) if (m := regex_data.search(l))]
    valores = [{'linha': i, 'valor': m.group(1)} for i, l in enumerate(linhas) if (m := regex_valor.search(l))]
    identificadores = [{'linha': i, 'match': m} for i, l in enumerate(linhas) if (m := regex_identificador.search(l))]
    descricoes = [{'linha': i, 'desc': m.group(1)} for i, l in enumerate(linhas) if (m := regex_descricao.search(l))]

    print(f"INFO: Mapeamento: {len(datas)} Datas, {len(descricoes)} Descrições, {len(valores)} Valores, {len(identificadores)} Identificadores")
    
    carro_padrao, placa_padrao = None, None
    if identificadores:
        match_id_padrao = identificadores[0]['match']
        carro_padrao = match_id_padrao.group(1).strip()
        placa_padrao = match_id_padrao.group(2).strip()

    if not carro_padrao:
        return []

    num_pares = min(len(descricoes), len(valores))
    for i in range(num_pares):
        desc_info = descricoes[i]
        val_info = valores[i]
        linha_ref = desc_info['linha']
        data_correta = next((d['data'] for d in reversed(datas) if d['linha'] <= linha_ref), None)
        
        if data_correta:
            valor_bruto_str = val_info['valor']
            valor_corrigido_str = valor_bruto_str.replace(',', '.')
            if '.' not in valor_corrigido_str and len(valor_corrigido_str) > 2:
                valor_corrigido_str = valor_corrigido_str[:-2] + '.' + valor_corrigido_str[-2:]
            
            descricao_limpa = "Estacionamento" if "Estacionamento" in desc_info['desc'] else "Passagem"
            
            # Gera um ID único para evitar que transações iguais sejam descartadas
            id_transacao = f"{data_correta}_{valor_corrigido_str}_{i}"
            
            transacao_mapeada = {
                "ID_Transacao": id_transacao,
                "Data": data_correta,
                "Tipo de Despesa": descricao_limpa,
                "Estabelecimento": f"Concessionaria {carro_padrao}",
                "Valor": float(valor_corrigido_str),
                "Observação": f"Placa: {placa_padrao}"
            }
            transacoes_finais.append(transacao_mapeada)
            
    return transacoes_finais

# --- Função de preenchimento da planilha ---
def preencher_planilha_reembolso(transacoes, arquivo_modelo, arquivo_destino, nome_da_aba, linha_dos_totais):
    if not transacoes:
        print("AVISO: Nenhuma transação para preencher.")
        return

    print(f"INFO: Preenchendo {len(transacoes)} transações em '{arquivo_destino}' na aba '{nome_da_aba}'...")

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
            sheet[f'C{linha_atual}'] = transacao['Estabelecimento'] + ' - ' + transacao['Observação']
            sheet[f'D{linha_atual}'] = transacao['Tipo de Despesa']
            sheet[f'F{linha_atual}'] = "São Jose dos Campos"
            sheet[f'G{linha_atual}'] = "São Paulo"
            sheet[f'I{linha_atual}'] = transacao['Valor']
            
            linha_atual += 1

        workbook.save(arquivo_destino)
        print("INFO: Planilha de reembolso atualizada com sucesso!")

    except Exception as e:
        print(f"ERRO CRÍTICO ao preencher a planilha: {e}")

# --- Bloco principal ---
if __name__ == "__main__":
    NOME_DA_ABA = "Plan2"
    LINHA_DOS_TOTAIS = 46
    ARQUIVO_MODELO = "planilha_reembolso_branco.xlsx"
    ARQUIVO_DESTINO = "reembolso_preenchido.xlsx"
    
    if not os.path.exists(ARQUIVO_MODELO):
        print(f"ERRO FATAL: O arquivo modelo '{ARQUIVO_MODELO}' não foi encontrado.")
    else:
        imagens_para_processar = [
            "pedagios/pedagio1.jpg",
            "pedagios/pedagio2.jpg",
            "pedagios/pedagio3.jpg",
            "pedagios/pedagio4.jpg"
        ]
        
        todas_as_transacoes = []
        for caminho_imagem in imagens_para_processar:
            texto_extraido = extrair_texto_da_imagem(caminho_imagem)
            if texto_extraido:
                lista_de_transacoes = analisar_e_estruturar_texto(texto_extraido)
                if lista_de_transacoes:
                    todas_as_transacoes.extend(lista_de_transacoes)
        
        if todas_as_transacoes:
            df_final = pd.DataFrame(todas_as_transacoes)
            
            print(f"\n--- RESUMO FINAL COM {len(df_final)} TRANSAÇÕES ---")
            print(df_final[["ID_Transacao", "Data", "Tipo de Despesa", "Valor"]])
            
            preencher_planilha_reembolso(
                df_final.to_dict('records'),
                ARQUIVO_MODELO,
                ARQUIVO_DESTINO,
                NOME_DA_ABA,
                LINHA_DOS_TOTAIS
            )

        print("\nINFO: Processo finalizado.")
