import cv2
import pytesseract
import pandas as pd
import re
import os

def extrair_texto_da_imagem(caminho_imagem):
    print(f"\nINFO: Lendo a imagem com OCR: {caminho_imagem}")
    try:
        imagem = cv2.imread(caminho_imagem)
        if imagem is None:
            print(f"ERRO: Não foi possível carregar a imagem. Verifique o caminho.")
            return None
        imagem_cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
        texto_bruto = pytesseract.image_to_string(imagem_cinza, lang='por')
        if not texto_bruto.strip():
            print("AVISO: Nenhum texto foi encontrado na imagem.")
            return None
        return texto_bruto
    except Exception as e:
        print(f"ERRO: Ocorreu um erro inesperado durante o OCR: {e}")
        return None



def analisar_e_estruturar_texto(texto_bruto):
    print("INFO: Analisando e estruturando o texto extraído com a lógica de 'memória'...")
    transacoes_list = []
    data_atual = None
    transacao_pendente = None

    ultimo_identificador_conhecido = None

    linhas = texto_bruto.strip().split('\n')
    
    regex_data = re.compile(r"(\d{1,2} de \w+)")
    regex_transacao = re.compile(r"([a-zA-Z\s]*?)\s*-?R\$\s*(\d+[,.]?\d*)")
    regex_identificador = re.compile(r"(\d{3})\s*-?\s*([A-Z0-9]{7})")

    for linha in linhas:
        if not linha.strip():
            continue

        match_data = regex_data.search(linha)
        match_transacao = regex_transacao.search(linha)
        match_identificador = regex_identificador.search(linha)

        if match_data:
            # Se achamos uma nova data, qualquer transação pendente anterior perdeu seu identificador
            if transacao_pendente and ultimo_identificador_conhecido:
                print("AVISO: Transação pendente encontrada antes de uma nova data. Usando último identificador conhecido.")
                transacao_pendente.update(ultimo_identificador_conhecido)
                transacoes_list.append(transacao_pendente)

            data_atual = match_data.group(1).strip()
            print(f"INFO: Contexto de data atualizado para: {data_atual}")
            transacao_pendente = None
        
        elif match_transacao:
            # Se já existia uma transação pendente, ela perdeu seu identificador.
            if transacao_pendente and ultimo_identificador_conhecido:
                print(f"AVISO: Transação pendente ({transacao_pendente['descricao']} {transacao_pendente['valor']}) encontrada antes de uma nova. Usando último identificador.")
                transacao_pendente.update(ultimo_identificador_conhecido)
                transacoes_list.append(transacao_pendente)
            
            descricao_bruta = match_transacao.group(1).strip()
            valor_bruto_str = match_transacao.group(2)
            
            valor_corrigido_str = valor_bruto_str.replace(',', '.')
            if '.' not in valor_corrigido_str and len(valor_corrigido_str) > 2:
                valor_corrigido_str = valor_corrigido_str[:-2] + '.' + valor_corrigido_str[-2:]
            
            descricao_limpa = "Passagem"
            if "Estacionamento" in descricao_bruta:
                descricao_limpa = "Estacionamento"
            
            transacao_pendente = {
                "Data": data_atual,
                "Descrição": descricao_limpa,
                "Valor": float(valor_corrigido_str)
            }

        elif match_identificador:
            carro = match_identificador.group(1).strip()
            placa = match_identificador.group(2).strip()
            # Atualiza nossa "memória" com o último identificador válido
            ultimo_identificador_conhecido = {"Carro": carro, "Placa": placa}

            if transacao_pendente:
                # Se há uma transação esperando, combina com este identificador
                transacao_pendente.update(ultimo_identificador_conhecido)
                transacoes_list.append(transacao_pendente)
                transacao_pendente = None # Limpa a pendência

    if transacao_pendente and ultimo_identificador_conhecido:
        print("AVISO: Processando última transação do arquivo que não tinha identificador.")
        transacao_pendente.update(ultimo_identificador_conhecido)
        transacoes_list.append(transacao_pendente)

    return transacoes_list


def salvar_em_excel(transacoes, nome_arquivo="pedagios.xlsx"):
    if not transacoes:
        print("AVISO: Nenhuma transação foi encontrada para salvar.")
        return
    print(f"INFO: Salvando {len(transacoes)} transações no arquivo '{nome_arquivo}'...")
    novo_df = pd.DataFrame(transacoes)
    if os.path.exists(nome_arquivo):
        try:
            existente_df = pd.read_excel(nome_arquivo)
            final_df = pd.concat([existente_df, novo_df], ignore_index=True)
            final_df.drop_duplicates(subset=['Data', 'Descrição', 'Valor', 'Placa'], keep='first', inplace=True, ignore_index=True)
        except Exception as e:
            print(f"AVISO: Não foi possível ler o arquivo Excel existente. Criando um novo. Erro: {e}")
            final_df = novo_df
    else:
        final_df = novo_df
    final_df.to_excel(nome_arquivo, index=False)
    print("INFO: Dados salvos com sucesso no Excel!")


if __name__ == "__main__":
    imagens_para_processar = [
        "pedagios/pedagio1.jpg",
        "pedagios/pedagio2.jpg",
        "pedagios/pedagio3.jpg"
    ]
    todas_as_transacoes = []
    for caminho_imagem in imagens_para_processar:
        if not os.path.exists(caminho_imagem):
            print(f"AVISO: Imagem não encontrada, pulando: {caminho_imagem}")
            continue
        texto_extraido = extrair_texto_da_imagem(caminho_imagem)
        if texto_extraido:
            lista_de_transacoes = analisar_e_estruturar_texto(texto_extraido)
            if lista_de_transacoes:
                todas_as_transacoes.extend(lista_de_transacoes)
    if todas_as_transacoes:
        print("\n--- RESUMO DE TODAS AS TRANSAÇÕES ENCONTRADAS ---")
        for t in todas_as_transacoes:
            print(t)
        print("-------------------------------------------------")
        salvar_em_excel(todas_as_transacoes)
    print("\nINFO: Processo finalizado.")