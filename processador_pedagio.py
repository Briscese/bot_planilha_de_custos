import cv2
import pytesseract
import pandas as pd
import re
import os
import locale

try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    print("AVISO: Locale 'pt_BR.UTF-8' não pôde ser configurado.")

def extrair_texto_da_imagem(caminho_imagem):
    print(f"\nINFO: Lendo a imagem com OCR: {caminho_imagem}")
    try:
        imagem = cv2.imread(caminho_imagem)
        if imagem is None: return None
        imagem_cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
        texto_bruto = pytesseract.image_to_string(imagem_cinza, lang='por')
        
        print(f"\n=============== TEXTO BRUTO DE: {caminho_imagem} =============== ")
        print(texto_bruto)
        print("======================================================================\n")
        return texto_bruto if texto_bruto.strip() else None
    except Exception as e:
        print(f"ERRO durante o OCR: {e}")
        return None

def analisar_e_estruturar_texto(texto_bruto):
    print("INFO: Analisando com a lógica de pareamento por ordem...")
    transacoes_finais = []
    
    linhas = texto_bruto.strip().split('\n')
    
    regex_data = re.compile(r"(\d{1,2} de \w+)")
    regex_valor = re.compile(r"R\$\s*(\d+[,.]?\d*)")
    regex_identificador = re.compile(r"(\d{3})\s*-?\s*([A-Z0-9]{7})")
    regex_descricao = re.compile(r"(Passagem|Estacionamento)", re.IGNORECASE)

    # 1. Mapear todas as peças e suas localizações
    datas = [{'linha': i, 'data': m.group(1).strip()} for i, l in enumerate(linhas) if (m := regex_data.search(l))]
    valores = [{'linha': i, 'valor': m.group(1)} for i, l in enumerate(linhas) if (m := regex_valor.search(l))]
    identificadores = [{'linha': i, 'match': m} for i, l in enumerate(linhas) if (m := regex_identificador.search(l))]
    descricoes = [{'linha': i, 'desc': m.group(1)} for i, l in enumerate(linhas) if (m := regex_descricao.search(l))]

    print(f"INFO: Mapeamento: {len(datas)} Datas, {len(descricoes)} Descrições, {len(valores)} Valores, {len(identificadores)} Identificadores")
    
    # Encontra o carro/placa uma vez para usar como padrão
    carro_padrao, placa_padrao = None, None
    if identificadores:
        match_id_padrao = identificadores[0]['match']
        carro_padrao = match_id_padrao.group(1).strip()
        placa_padrao = match_id_padrao.group(2).strip()

    # 2. Parear descrições e valores pela ordem em que aparecem
    num_pares = min(len(descricoes), len(valores))
    for i in range(num_pares):
        desc_info = descricoes[i]
        val_info = valores[i]
        
        # Usa a linha da descrição como referência para encontrar a data
        linha_ref = desc_info['linha']
        data_correta = next((d['data'] for d in reversed(datas) if d['linha'] <= linha_ref), None)
        
        if data_correta:
            valor_bruto_str = val_info['valor']
            valor_corrigido_str = valor_bruto_str.replace(',', '.')
            if '.' not in valor_corrigido_str and len(valor_corrigido_str) > 2:
                valor_corrigido_str = valor_corrigido_str[:-2] + '.' + valor_corrigido_str[-2:]
            
            descricao_limpa = "Estacionamento" if "Estacionamento" in desc_info['desc'] else "Passagem"
            
            transacoes_finais.append({
                "Data": data_correta,
                "Descrição": descricao_limpa,
                "Valor": float(valor_corrigido_str),
                "Carro": carro_padrao,
                "Placa": placa_padrao
            })

    return transacoes_finais

def salvar_em_excel(transacoes_dict, nome_arquivo="pedagios.xlsx"):
    if not transacoes_dict:
        print("AVISO: Nenhuma transação para salvar.")
        return
        
    df = pd.DataFrame(transacoes_dict)
    
    # Adiciona um ano fixo para permitir a ordenação correta das datas
    df['Data_Completa'] = pd.to_datetime(df['Data'] + f' {pd.Timestamp.now().year}', format='%d de %B %Y', errors='coerce', dayfirst=True)
    df.dropna(subset=['Data_Completa'], inplace=True)
    df = df.sort_values(by='Data_Completa', ascending=False).drop(columns=['Data_Completa'])
    
    # Adiciona os dados ao arquivo existente ou cria um novo
    if os.path.exists(nome_arquivo):
        try:
            existente_df = pd.read_excel(nome_arquivo)
            final_df = pd.concat([existente_df, df], ignore_index=True)
        except Exception as e:
            print(f"AVISO: Não foi possível ler Excel existente: {e}")
            final_df = df
    else:
        final_df = df

    print(f"INFO: Total de transações para salvar: {len(final_df)}")
    final_df.to_excel(nome_arquivo, index=False)
    print(f"INFO: Dados salvos com sucesso em '{nome_arquivo}'!")

if __name__ == "__main__":
    imagens_para_processar = ["pedagios/pedagio1.jpg", "pedagios/pedagio2.jpg", "pedagios/pedagio3.jpg", "pedagios/pedagio4.jpg"]
    
    todas_as_transacoes = []
    for caminho_imagem in imagens_para_processar:
        texto_extraido = extrair_texto_da_imagem(caminho_imagem)
        if texto_extraido:
            lista_de_transacoes = analisar_e_estruturar_texto(texto_extraido)
            if lista_de_transacoes:
                todas_as_transacoes.extend(lista_de_transacoes)
    
    if todas_as_transacoes:
        df_final = pd.DataFrame(todas_as_transacoes)
        
        print("\n--- RESUMO DE TODAS AS TRANSAÇÕES ENCONTRADAS ---")
        registros_finais = df_final.to_dict('records')
        print(f"Total de registros únicos: {len(registros_finais)}")
        for t in registros_finais:
            print(t)
        print("-------------------------------------------------")
        salvar_em_excel(registros_finais)

    print("\nINFO: Processo finalizado.")