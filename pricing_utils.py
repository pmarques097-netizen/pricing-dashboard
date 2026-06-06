import pandas as pd
import os


def carregar_pasta_excel(pasta):

    dfs = []

    if not os.path.exists(pasta):
        return pd.DataFrame()

    for arquivo in os.listdir(pasta):

        caminho = os.path.join(
            pasta,
            arquivo
        )

        if arquivo.lower().endswith(".xlsx"):

            try:
                df = pd.read_excel(caminho)
                df["Arquivo_Origem"] = arquivo
                dfs.append(df)
            except Exception:
                pass

        elif arquivo.lower().endswith(".xls"):

            try:
                df = pd.read_excel(caminho)
                df["Arquivo_Origem"] = arquivo
                dfs.append(df)
            except Exception:
                pass

        elif arquivo.lower().endswith(".csv"):

            try:
                df = pd.read_csv(
                    caminho,
                    sep=None,
                    engine="python",
                    encoding="utf-8"
                )
                df["Arquivo_Origem"] = arquivo
                dfs.append(df)
            except Exception:

                try:
                    df = pd.read_csv(
                        caminho,
                        sep=None,
                        engine="python",
                        encoding="latin1"
                    )
                    df["Arquivo_Origem"] = arquivo
                    dfs.append(df)
                except Exception:
                    pass

    if len(dfs) == 0:
        return pd.DataFrame()

    base = pd.concat(
        dfs,
        ignore_index=True
    )

    base.columns = (
        base.columns
        .astype(str)
        .str.strip()
    )

    return base


def carregar_historico():

    historico = carregar_pasta_excel(
        "VENDA_TESTE"
    )

    if historico.empty:
        return pd.DataFrame()

    if "Data Emissão" in historico.columns:

        historico["Data Emissão"] = pd.to_datetime(
            historico["Data Emissão"],
            errors="coerce",
            dayfirst=True
        )

    return historico


def carregar_compra():

    pasta = "COMPRA_TESTE"

    dfs = []

    if not os.path.exists(pasta):
        return pd.DataFrame()

    for arquivo in os.listdir(pasta):

        caminho = os.path.join(
            pasta,
            arquivo
        )

        if arquivo.lower().endswith((".xlsx", ".xls")):

            try:

                df = pd.read_excel(
                    caminho,
                    header=2
                )

                df["Arquivo_Origem"] = arquivo

                dfs.append(df)

            except Exception:
                pass

    if len(dfs) == 0:
        return pd.DataFrame()

    compra = pd.concat(
        dfs,
        ignore_index=True
    )

    compra.columns = (
        compra.columns
        .astype(str)
        .str.strip()
    )

    compra = compra.rename(
        columns={
            "Rótulos de Linha": "Marca",
            "Soma de Valor Líquido": "Valor_Liquido",
            "PART%": "Participacao",
            "GT%": "Acumulado"
        }
    )

    return compra


def carregar_venda_rede():

    return carregar_pasta_excel(
        "VENDA_FINAL_TESTE"
    )


def carregar_estoque():

    return carregar_pasta_excel(
        "ESTOQUE_TESTE"
    )


def identificar_rede(nome):

    nome_original = str(nome).strip()
    nome_base = nome_original.upper()

    regras = {
        "RAIADROGASIL": "Drogasil",
        "DROGASIL": "Drogasil",
        "DROGA RAIA": "Droga Raia",
        "RAIA": "Droga Raia",
        "PAGUE MENOS": "Pague Menos",
        "ULTRAPOPULAR": "Ultra Popular",
        "ULTRA POPULAR": "Ultra Popular",
        "SAO JOAO": "São João",
        "SÃO JOÃO": "São João",
        "PANVEL": "Panvel",
        "NISSEI": "Nissei",
        "EXTRAFARMA": "Extrafarma",
        "PACHECO": "Pacheco",
        "VENANCIO": "Venancio",
        "VENÂNCIO": "Venancio",
        "DPSP": "DPSP",
        "DROGARIA SAO PAULO": "Drogaria São Paulo",
        "DROGARIA SÃO PAULO": "Drogaria São Paulo",
        "DROGARIAS PACHECO": "Pacheco",
        "PRECO POPULAR": "Preço Popular",
        "PREÇO POPULAR": "Preço Popular",
        "INDIANA": "Indiana",
        "ARAUJO": "Araujo",
        "ARAÚJO": "Araujo",
        "DROGAL": "Drogal",
        "DROGASMIL": "Drogasmil",
        "GLOBO": "Globo"
    }

    for chave, rede in regras.items():

        if chave in nome_base:
            return rede

    remover = [
        "FARMACIA",
        "FARMÁCIA",
        "DROGARIA",
        "DROGARIAS",
        "DROGA",
        "MEDICAMENTOS",
        "MEDICAMENTO",
        "COMERCIO",
        "COMÉRCIO",
        "PRODUTOS",
        "FARMACEUTICOS",
        "FARMACÊUTICOS",
        "PERFUMARIA",
        "PERFUMARIAS",
        "COSMETICOS",
        "COSMÉTICOS",
        "LTDA",
        "EIRELI",
        "ME",
        "EPP",
        "SA",
        "S/A",
        "S.A.",
        "MATRIZ",
        "FILIAL",
        "LOJA",
        "CIA",
        "COMPANHIA"
    ]

    resumo = nome_base

    for palavra in remover:
        resumo = resumo.replace(
            palavra,
            " "
        )

    resumo = " ".join(
        resumo.split()
    )

    if resumo == "":
        resumo = nome_original

    palavras = (
        resumo
        .title()
        .split()
    )

    return " ".join(
        palavras[:3]
    )


def curva_abc(df):

    if "Ganho_Potencial" not in df.columns:
        return pd.DataFrame()

    produto_col = (
        "Descricao_Unica"
        if "Descricao_Unica" in df.columns
        else "Produto"
    )

    ranking = (
        df.groupby(produto_col)
        ["Ganho_Potencial"]
        .sum()
        .reset_index()
        .rename(columns={produto_col: "Produto"})
        .sort_values(
            "Ganho_Potencial",
            ascending=False
        )
    )

    total = ranking["Ganho_Potencial"].sum()

    if total == 0:

        ranking["ABC"] = "C"

        return ranking

    ranking["Perc_Acum"] = (
        ranking["Ganho_Potencial"]
        .cumsum()
        / total
    )

    ranking["ABC"] = ranking["Perc_Acum"].apply(
        lambda x:
        "A" if x <= 0.80
        else "B" if x <= 0.95
        else "C"
    )

    return ranking
