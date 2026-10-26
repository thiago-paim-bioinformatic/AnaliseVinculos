import os
import pandas as pd
import networkx as nx
from pyvis.network import Network

def carrega_dados_extrato_detalhado (path:str) -> pd.DataFrame:
    dataframe = pd.read_csv(path, sep=";", encoding='iso-8859-1')

    #converte todas as colunas em strings
    dataframe = dataframe.astype("str")

    #colunas numericas monetárias
    columns = ["VALOR_SALDO", "VALOR_TRANSACAO"]
    for column in columns:
        dataframe[column] = dataframe[column].str.replace(",", ".").astype("float64")

    #coluna de data
    dataframe["DATA_LANCAMENTO"] = pd.to_datetime(dataframe["DATA_LANCAMENTO"], format="%d/%m/%Y")

    #formata colunas de cpf e cnpj
    dataframe["CPF_CNPJ_OD"] = dataframe["CPF_CNPJ_OD"].str.replace(".0", "")
    #preenche zeros a esquerda
    columns = ["CPF_CNPJ_OD", "CPF_CNPJ_TITULAR"]
    for column in columns:
        dataframe[column] = dataframe[column].str.zfill(14)

    return dataframe

def soma_valor_transacao_titular_OD (dataframe) -> pd.DataFrame:
    sumarizacao_valor_transacao = dataframe.groupby(["CPF_CNPJ_TITULAR","NOME_TITULAR","NATUREZA_LANCAMENTO","CPF_CNPJ_OD", "NOME_PESSOA_OD"])["VALOR_TRANSACAO"].agg(
        VALOR_TOTAL_MOVIMENTADO = 'sum',
        QTD_TRANSACOES = 'count',
        MEDIANA_TRANSACOES = 'median',
        MENOR_TRANSACAO = 'min',
        MAIOR_TRANSACAO = 'max').reset_index()

    df_sumarizacao_valor_transacao = pd.DataFrame(sumarizacao_valor_transacao)

    #converte todas as colunas em strings
    df_sumarizacao_valor_transacao = df_sumarizacao_valor_transacao.astype("str")
    df_sumarizacao_valor_transacao["CPF_CNPJ_OD"] = df_sumarizacao_valor_transacao["CPF_CNPJ_OD"].str.replace(".0", "")

    #colunas numericas monetárias
    for coluna in ["VALOR_TOTAL_MOVIMENTADO", "MEDIANA_TRANSACOES", "MENOR_TRANSACAO", "MAIOR_TRANSACAO"]:
        df_sumarizacao_valor_transacao[coluna] = df_sumarizacao_valor_transacao[coluna].astype("float64")

    #inteiros: coluna de quantidade de transacoes
    df_sumarizacao_valor_transacao["QTD_TRANSACOES"] = df_sumarizacao_valor_transacao["QTD_TRANSACOES"].astype("int")

    #preenche zeros a esquerda
    columns = ["CPF_CNPJ_OD", "CPF_CNPJ_TITULAR"]
    for column in columns:
        df_sumarizacao_valor_transacao[column] = df_sumarizacao_valor_transacao[column].str.zfill(14)


    return df_sumarizacao_valor_transacao


def criar_rede(input_dataframe:pd.DataFrame, name_network:str | None="rede") -> Network:
    min_valor = input_dataframe['VALOR_TOTAL_MOVIMENTADO'].min()
    max_valor = input_dataframe['VALOR_TOTAL_MOVIMENTADO'].max()

    # Margem para evitar divisão por zero se todos os valores forem iguais
    if max_valor == min_valor:
        max_valor += 1

    net = Network(
        height="750px",
        width="100%",
        bgcolor="#222222",
        font_color="white",
        notebook=True, # caso esteja rodando em notebook
        directed=True #grafo direcionado
    )
    net.force_atlas_2based(
        gravity=-300,           # Força de repulsão moderada
        central_gravity=0.05,   # Força que puxa os nós de volta para o centro
        spring_length=600,      # Distância padrão entre os nós conectados
        damping=0.8
    )

    for idx, row in input_dataframe.iterrows():
        orientacao = row['NATUREZA_LANCAMENTO']
        titular = row['NOME_TITULAR']
        id_titular = row['CPF_CNPJ_TITULAR']
        od = row['NOME_PESSOA_OD']
        id_od = row['CPF_CNPJ_OD']
        valor = row['VALOR_TOTAL_MOVIMENTADO']
        contagem = row['QTD_TRANSACOES']

        # Criando um texto explicativo para quando passar o mouse por cima (Tooltip)
        info_conexao = f"Total: R$ {valor:,.2f}\nTransações: {contagem}"

        # Adiciona o nó de origem (Titular),
        net.add_node(id_titular, label=titular, title=f"Titular: {titular}\nCPF/CNPJ: {id_titular}", color="#4791db")

        # Adiciona o nó de destino,
        net.add_node(id_od, label=od, title=f"OD: {od}\nCPF/CNPJ: {id_od}", color="#e57373")
        # Define os limites visuais das linhas na tela
        espessura_minima = 1
        espessura_maxima = 4

        # Calcula a proporção do valor atual dentro do range
        proporcao = (valor - min_valor) / (max_valor - min_valor)

        # Aplica a proporção na escala de espessura desejada
        peso_linha = espessura_minima + (proporcao * (espessura_maxima - espessura_minima))

        if orientacao == 'D':
            net.add_edge(id_titular, 
                         id_od, 
                         title=info_conexao, 
                         arrows={
                            "to": {
                                "enabled": True, 
                                "scaleFactor": 0.5  # Reduz o tamanho do triângulo da seta pela metade
                            }
                        },
                         width=peso_linha, 
                         color="#ffffff")

        elif orientacao == 'C':
            net.add_edge(id_titular, 
                         id_od, 
                         title=info_conexao, 
                         arrows={
                            "from": {
                                "enabled": True, 
                                "scaleFactor": 0.5  # Reduz o tamanho do triângulo da seta pela metade
                            }
                        },
	                 width=peso_linha, 
                         color="#ffffff")
        else:
            net.add_edge(id_titular, 
                         id_od, 
                         title=info_conexao, 
                         arrows={
                            "to,from": {
                                "enabled": False, 
                                "scaleFactor": 0.5  # Reduz o tamanho do triângulo da seta pela metade
                            }
                        },
                         width=peso_linha, 
                         color="#ffffff")


    # 4. Ativar botões de controle de física para você arrastar e ajustar o gráfico na tela,
    net.show_buttons(filter_=['physics'])

    # 5. Salva e abre o gráfico interativo no navegador,
    net.write_html(f"{name_network}.html")
    return net.show(f"{name_network}.html")




def rede_conectada(input_dataframe: pd.DataFrame, name_network: str = "rede", type_graph:str | None="consolidado") -> Network:
    # 1. Instanciar como MultiDiGraph para permitir múltiplas arestas entre os mesmos nós
    G = nx.MultiDiGraph()
    
    nos_info = {}

    if type_graph == "consolidado":
        # O cálculo de min/max precisa mapear todas as linhas originais do DataFrame
        min_valor = input_dataframe['VALOR_TOTAL_MOVIMENTADO'].min()
        max_valor = input_dataframe['VALOR_TOTAL_MOVIMENTADO'].max()
        if max_valor == min_valor:
            max_valor += 1

        espessura_minima = 1
        espessura_maxima = 6

        # 2. Alimentar o grafo mantendo cada transação única
        for idx, row in input_dataframe.iterrows():
            orientacao = row['NATUREZA_LANCAMENTO']
            titular = row['NOME_TITULAR']
            id_titular = row['CPF_CNPJ_TITULAR']
            od = row['NOME_PESSOA_OD']
            id_od = row['CPF_CNPJ_OD']
            valor = row['VALOR_TOTAL_MOVIMENTADO']
            contagem = row['QTD_TRANSACOES']

            # Define a direção real do fluxo com base na natureza
            if orientacao == 'D':    # Débito: Titular envia para OD
                u, v = id_titular, id_od
            elif orientacao == 'C':  # Crédito: OD envia para Titular
                u, v = id_od, id_titular
            else:
                u, v = id_titular, id_od

            # Armazena os dados dos nós para criação posterior
            nos_info[id_titular] = {"label": titular, "title": f"Titular: {titular}\nCPF/CNPJ: {id_titular}", "color": "#4791db"}
            nos_info[id_od] = {"label": od, "title": f"Destino: {od}\nCPF/CNPJ: {id_od}", "color": "#e57373"}

            # Calcula a espessura desta transação específica
            proporcao = (valor - min_valor) / (max_valor - min_valor)
            peso_linha = espessura_minima + (proporcao * (espessura_maxima - espessura_minima))

            # Adiciona a aresta isolada no MultiDiGraph
            G.add_edge(
                u, v,
                valor=valor,
                width=peso_linha,
                title=f"Transação {idx}\nTotal: R$ {valor:,.2f}\nQtd: {contagem}",
                color="#ffffff"
            )

    if type_graph == "analitico":

        # O cálculo de min/max precisa mapear todas as linhas originais do DataFrame
        min_valor = input_dataframe['VALOR_TRANSACAO'].min()
        max_valor = input_dataframe['VALOR_TRANSACAO'].max()
        if max_valor == min_valor:
            max_valor += 1

        espessura_minima = 1
        espessura_maxima = 6

        # 2. Alimentar o grafo mantendo cada transação única
        for idx, row in input_dataframe.iterrows():

            #numero_caso = row['ï»¿NUMERO_CASO'] 
            numero_banco = str(row['NUMERO_BANCO'])
            #nome_banco = row['NOME_BANCO'] 
            numero_agencia = str(row['NUMERO_AGENCIA'])
            numero_conta = str(row['NUMERO_CONTA']) 
            #tipo = row['TIPO'] 
            nome_titular = str(row['NOME_TITULAR']) 
            cpf_cnpj_titular = str(row['CPF_CNPJ_TITULAR'])
            descricao_lancamento = str(row['DESCRICAO_LANCAMENTO']) 
            #cnab = row['CNAB'] 
            data_lancamento = str(row['DATA_LANCAMENTO']) 
            #numero_documento = row['NUMERO_DOCUMENTO']
            #numero_documento_transacao = row['NUMERO_DOCUMENTO_TRANSACAO'] 
            local_transacao = row['LOCAL_TRANSACAO'] 
            valor_transacao = row['VALOR_TRANSACAO']
            natureza_lancamento = str(row['NATUREZA_LANCAMENTO'])
            #valor_saldo = row['VALOR_SALDO'] 
            #natureza_saldo = row['NATUREZA_SALDO'] 
            cpf_cnpj_od = str(row['CPF_CNPJ_OD'])
            nome_pessoa_od = str(row['NOME_PESSOA_OD']) 
            #tipo_pessoa_od = row['TIPO_PESSOA_OD'] 
            numero_banco_od = str(row['NUMERO_BANCO_OD'])
            numero_agencia_od = str(row['NUMERO_AGENCIA_OD']) 
            numero_conta_od = str(row['NUMERO_CONTA_OD']) 
            #observacao = row['OBSERVACAO']
            #nome_endossante_cheque = row['NOME_ENDOSSANTE_CHEQUE'] 
            #doc_endossante_cheque = row['DOC_ENDOSSANTE_CHEQUE']

            # Define a direção real do fluxo com base na natureza
            if natureza_lancamento == 'D':    # Débito: Titular envia para OD
                u, v = cpf_cnpj_titular, cpf_cnpj_od
            elif natureza_lancamento == 'C':  # Crédito: OD envia para Titular
                u, v = cpf_cnpj_od, cpf_cnpj_titular
            else:
                u, v = cpf_cnpj_titular, cpf_cnpj_od

            # Armazena os dados dos nós para criação posterior
            nos_info[cpf_cnpj_titular] = {"label": nome_titular, "title": f"Titular: {nome_titular}\nCPF/CNPJ: {cpf_cnpj_titular}", "color": "#4791db"}
            nos_info[cpf_cnpj_od] = {"label": nome_pessoa_od, "title": f"OD: {nome_pessoa_od}\nCPF/CNPJ: {cpf_cnpj_od}", "color": "#e57373"}

            # Calcula a espessura desta transação específica
            proporcao = (valor_transacao - min_valor) / (max_valor - min_valor)
            peso_linha = espessura_minima + (proporcao * (espessura_maxima - espessura_minima))

            # Adiciona a aresta isolada no MultiDiGraph
            G.add_edge(
                u, v,
                valor=valor_transacao,
                width=peso_linha,
                title=f"Transação {idx}\nValor: R$ {valor_transacao:,.2f}\nData: {data_lancamento}\nBanco Titular: {numero_banco}\nAgência Titular: {numero_agencia}\nConta Titular: {numero_conta}\n\nBanco OD: {numero_banco_od}\nAgência OD: {numero_agencia_od}\nConta OD: {numero_conta_od}\n\nDescrição: {descricao_lancamento}",
                color="#ffffff"
            )

    # Adiciona os nós únicos ao grafo
    for node_id, attrs in nos_info.items():
        if node_id and node_id.lower() != 'nan':
            G.add_node(str(node_id), **attrs)

    # 3. Configurar o PyVis
    net = Network(
        height="750px",
        width="100%",
        bgcolor="#222222",
        font_color="white",
        notebook=True,
        directed=True
    )
    
    net.force_atlas_2based(
        gravity=-300,
        central_gravity=0.05,
        spring_length=300,
        damping=0.8
    )

    # Importa a estrutura de MultiDiGraph do NetworkX
    net.from_nx(G)

    # 4. Configurar curvas e setas para múltiplas arestas
    for edge in net.edges:
        edge['arrows'] = {
            'to': {
                'enabled': True,
                'scaleFactor': 0.5
            }
        }
        # Força as linhas a curvarem dinamicamente para não se sobreporem
        edge['smooth'] = {
            'enabled': True,
            'type': 'dynamic',  # Faz com que cada linha paralela tome uma curvatura diferente
            'roundness': 0.5
        }

    net.show_buttons(filter_=['physics'])
    net.write_html(f"{name_network}.html")

    return net, G
