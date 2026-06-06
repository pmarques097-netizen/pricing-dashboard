import pandas as pd
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def limpar_colunas(df):

    if df.empty:
        return df

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
    )

    return df


def carregar_pasta_excel(nome_pasta, header=0):

    pasta = BASE_DIR / nome_pasta

    dfs = []

    if not pasta.exists():

        print(
            f"Pasta não encontrada: {pasta}"
        )

        return pd.DataFrame()

    arquivos = []

    arquivos.extend(
        list(pasta.glob("*.xlsx"))
    )

    arquivos.extend(
        list(pasta.glob("*.xls"))
    )

    arquivos.extend(
        list(pasta.glob("*.csv"))
    )

    for arquivo in arquivos:

        try:

            if arquivo.suffix.lower() in [".xlsx", ".xls"]:

                df = pd.read_excel(
                    arquivo,
                    header=header
                )

            elif arquivo.suffix.lower() == ".csv":

                try:

                    df = pd.read_csv(
                        arquivo,
                        sep=None,
                        engine="python",
                        encoding="utf-8"
                    )

                except Exception:

                    df = pd.read_csv(
                        arquivo,
                        sep=None,
                        engine="python",
                        encoding="latin1"
                    )

            else:
                continue

            df["Arquivo_Origem"] = arquivo.name

            df = limpar_colunas(df)

            dfs.append(df)

        except Exception as erro:

            print(
                f"Erro ao ler {arquivo.name}: {erro}"
            )

    if len(dfs) == 0:
        return pd.DataFrame()

    base = pd.concat(
        dfs,
        ignore_index=True
    )

    base = limpar_colunas(base)

    return base


def carregar_historico():

    historico = carregar_pasta_excel(
        "VENDA_TESTE",
        header=0
    )

    if historico.empty:
        return pd.DataFrame()

    historico = limpar_colunas(historico)

    if "Data Emissão" in historico.columns:

        historico["Data Emissão"] = pd.to_datetime(
            historico["Data Emissão"],
            errors="coerce",
            dayfirst=True
        )

    return historico


def carregar_compra():

    compra = carregar_pasta_excel(
        "COMPRA_TESTE",
        header=2
    )

    if compra.empty:
        return pd.DataFrame()

    compra = limpar_colunas(compra)

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
        "VENDA_FINAL_TESTE",
        header=0
    )


def carregar_estoque():

    return carregar_pasta_excel(
        "ESTOQUE_TESTE",
        header=0
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
        "GLOBO": "Globo",
        "ZANOL": "Zanol e Thomaz",
        "THOMAZ": "Zanol e Thomaz",
        "TRIANGULO": "Triangulo",
        "TRIÂNGULO": "Triangulo",
        "BRASIFARMA": "Brasifarma"
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
        .rename(
            columns={
                produto_col: "Produto"
            }
        )
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
