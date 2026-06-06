import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------------------------------
# FORMATACAO BRASIL
# --------------------------------------------------

def moeda_br(valor):

    try:

        if pd.isna(valor):
            return ""

        return (
            f"R$ {float(valor):,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    except Exception:
        return ""


def numero_br(valor):

    try:

        if pd.isna(valor):
            return ""

        return (
            f"{float(valor):,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    except Exception:
        return ""


def percentual_br(valor):

    try:

        if pd.isna(valor):
            return ""

        return (
            f"{float(valor):,.2f}%"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    except Exception:
        return ""


from pricing_utils import (
carregar_historico,
carregar_compra,
carregar_venda_rede,
carregar_estoque,
identificar_rede,
curva_abc
)

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="Eirox Pricing Enterprise",
    layout="wide"
)

# --------------------------------------------------
# CSS
# --------------------------------------------------

try:

    with open(
        "style.css",
        encoding="utf-8"
    ) as f:

        st.markdown(
            f"<style>{f.read()}</style>",
            unsafe_allow_html=True
        )

except:
    pass

# --------------------------------------------------
# LOGO
# --------------------------------------------------

try:

    st.image(
        "logo eirox.png",
        width=350
    )

except:
    pass

st.title(
    "📊 Eirox - Ferramenta de Inteligência de Pricing (consulta e comparação de preços concorrência)"
)

# --------------------------------------------------
# DADOS
# --------------------------------------------------

@st.cache_data
def carregar():

    return pd.read_excel(
        "Analise_Pricing.xlsx"
    )

df = carregar()

historico = carregar_historico()
compra = carregar_compra()
venda_rede = carregar_venda_rede()
estoque = carregar_estoque()

# --------------------------------------------------
# PADRONIZAR COLUNAS
# --------------------------------------------------

df.columns = df.columns.astype(str).str.strip()

if not historico.empty:
    historico.columns = historico.columns.astype(str).str.strip()

# --------------------------------------------------
# DESCRICAO_UNICA POR EAN
# --------------------------------------------------

descricao_padrao = {}

# Base principal
if "EAN" in df.columns and "Produto" in df.columns:

    df["EAN"] = (
        df["EAN"]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.strip()
    )

    descricao_padrao = (
        df.groupby("EAN")["Produto"]
        .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else x.iloc[0])
        .to_dict()
    )

    df["Descricao_Unica"] = (
        df["EAN"].astype(str)
        + " - "
        + df["EAN"].map(descricao_padrao).fillna(df["Produto"]).astype(str)
    )

else:

    df["Descricao_Unica"] = (
        df["Produto"].astype(str)
        if "Produto" in df.columns
        else "SEM DESCRICAO"
    )

# Histórico
if not historico.empty:

    if "EAN (GTIN)" in historico.columns:
        historico["EAN"] = historico["EAN (GTIN)"]

    if "EAN" in historico.columns:
        historico["EAN"] = (
            historico["EAN"]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
        )

    if "EAN" in historico.columns and "Produto" in historico.columns:

        historico["Descricao_Unica"] = (
            historico["EAN"].astype(str)
            + " - "
            + historico["EAN"]
                .map(descricao_padrao)
                .fillna(historico["Produto"])
                .astype(str)
        )

    elif "Produto" in historico.columns:

        historico["Descricao_Unica"] = historico["Produto"].astype(str)

    else:

        historico["Descricao_Unica"] = "SEM DESCRICAO"


# --------------------------------------------------
# GANHO POTENCIAL PADRÃO SIMULADOR
# --------------------------------------------------

def encontrar_coluna_global(base, opcoes):

    for coluna in opcoes:

        if coluna in base.columns:
            return coluna

    return None


simulacao_global = pd.DataFrame()

if (
    not venda_rede.empty
    and not historico.empty
):

    venda_rede.columns = (
        venda_rede.columns
        .astype(str)
        .str.strip()
    )

    col_ean_venda_global = encontrar_coluna_global(
        venda_rede,
        [
            "EAN",
            "EAN (GTIN)",
            "GTIN",
            "Código de Barras",
            "Codigo de Barras",
            "CODIGO_BARRAS",
            "Cód. Barras",
            "Cod Barras",
            "Cód. Barras/Etiq.",
            "Cod. Barras/Etiq.",
            "Codigo Barras/Etiq",
            "Código Barras/Etiq"
        ]
    )

    col_produto_venda_global = encontrar_coluna_global(
        venda_rede,
        [
            "Produto",
            "Descrição",
            "Descricao",
            "DESCRICAO",
            "Nome Produto",
            "Embalagem"
        ]
    )

    col_qtd_global = encontrar_coluna_global(
        venda_rede,
        [
            "Quantidade",
            "Qtd",
            "QTD",
            "Qtde",
            "Quantidade Vendida",
            "Qtd Vendida",
            "Unidades",
            "UNIDADES",
            "Itens"
        ]
    )

    col_valor_total_global = encontrar_coluna_global(
        venda_rede,
        [
            "Venda",
            "Valor Venda",
            "Valor Total",
            "Total Venda",
            "Faturamento",
            "Valor Líquido",
            "Valor Liquido"
        ]
    )

    col_preco_atual_global = encontrar_coluna_global(
        venda_rede,
        [
            "Preço Venda",
            "Preco Venda",
            "Preço de Venda",
            "Preco de Venda",
            "Preço (R$)",
            "Preco (R$)",
            "Valor Unitário",
            "Valor Unitario",
            "Preço Médio",
            "Preco Medio",
            "Preco_Medio"
        ]
    )

    col_ean_hist_global = "EAN" if "EAN" in historico.columns else None

    if (
        col_ean_hist_global is None
        and "EAN (GTIN)" in historico.columns
    ):

        historico["EAN"] = historico["EAN (GTIN)"]
        col_ean_hist_global = "EAN"

    if (
        col_ean_venda_global
        and col_ean_hist_global
        and col_qtd_global
        and "Preço (R$)" in historico.columns
        and (
            col_preco_atual_global
            or col_valor_total_global
        )
    ):

        venda_rede["EAN"] = (
            venda_rede[col_ean_venda_global]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
        )

        historico["EAN"] = (
            historico[col_ean_hist_global]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
        )

        venda_rede[col_qtd_global] = pd.to_numeric(
            venda_rede[col_qtd_global],
            errors="coerce"
        )

        historico["Preço (R$)"] = pd.to_numeric(
            historico["Preço (R$)"],
            errors="coerce"
        )

        if col_valor_total_global:

            venda_rede[col_valor_total_global] = pd.to_numeric(
                venda_rede[col_valor_total_global],
                errors="coerce"
            )

        if col_preco_atual_global:

            venda_rede[col_preco_atual_global] = pd.to_numeric(
                venda_rede[col_preco_atual_global],
                errors="coerce"
            )

        mercado_global = (
            historico
            .dropna(
                subset=[
                    "EAN",
                    "Preço (R$)"
                ]
            )
            .groupby("EAN")
            ["Preço (R$)"]
            .min()
            .reset_index()
            .rename(
                columns={
                    "Preço (R$)": "Preco_Sugerido_Mercado"
                }
            )
        )

        if col_preco_atual_global:

            vendas_global = (
                venda_rede
                .dropna(
                    subset=[
                        "EAN",
                        col_qtd_global,
                        col_preco_atual_global
                    ]
                )
                .groupby("EAN")
                .agg({
                    col_qtd_global: "sum",
                    col_preco_atual_global: "mean"
                })
                .reset_index()
                .rename(
                    columns={
                        col_qtd_global: "Qtd_Vendida_Mes_Anterior",
                        col_preco_atual_global: "Preco_Atual"
                    }
                )
            )

            vendas_global["Venda_Preco_Antigo"] = (
                vendas_global["Qtd_Vendida_Mes_Anterior"]
                * vendas_global["Preco_Atual"]
            )

        else:

            vendas_global = (
                venda_rede
                .dropna(
                    subset=[
                        "EAN",
                        col_qtd_global,
                        col_valor_total_global
                    ]
                )
                .groupby("EAN")
                .agg({
                    col_qtd_global: "sum",
                    col_valor_total_global: "sum"
                })
                .reset_index()
                .rename(
                    columns={
                        col_qtd_global: "Qtd_Vendida_Mes_Anterior",
                        col_valor_total_global: "Venda_Preco_Antigo"
                    }
                )
            )

            vendas_global["Preco_Atual"] = (
                vendas_global["Venda_Preco_Antigo"]
                / vendas_global["Qtd_Vendida_Mes_Anterior"]
            )

        simulacao_global = vendas_global.merge(
            mercado_global,
            on="EAN",
            how="left"
        )

        if col_produto_venda_global:

            desc_global = (
                venda_rede
                .groupby("EAN")[col_produto_venda_global]
                .agg(
                    lambda x:
                    x.mode().iloc[0]
                    if not x.mode().empty
                    else x.iloc[0]
                )
                .reset_index()
                .rename(
                    columns={
                        col_produto_venda_global: "Produto_Simulador"
                    }
                )
            )

            simulacao_global = simulacao_global.merge(
                desc_global,
                on="EAN",
                how="left"
            )

        simulacao_global["Venda_Projetada_Preco_Sugerido"] = (
            simulacao_global["Qtd_Vendida_Mes_Anterior"]
            * simulacao_global["Preco_Sugerido_Mercado"]
        )

        simulacao_global["Ganho_Unitario"] = (
            simulacao_global["Preco_Sugerido_Mercado"]
            - simulacao_global["Preco_Atual"]
        )

        simulacao_global["Ganho_Potencial_Simulador"] = (
            simulacao_global["Venda_Projetada_Preco_Sugerido"]
            - simulacao_global["Venda_Preco_Antigo"]
        )

        simulacao_global = simulacao_global[
            simulacao_global["Ganho_Potencial_Simulador"] > 0
        ].copy()

        for coluna in [
            "Preco_Atual",
            "Preco_Sugerido_Mercado",
            "Ganho_Unitario",
            "Venda_Preco_Antigo",
            "Venda_Projetada_Preco_Sugerido",
            "Ganho_Potencial_Simulador",
            "Qtd_Vendida_Mes_Anterior"
        ]:

            if coluna in simulacao_global.columns:

                simulacao_global[coluna] = (
                    simulacao_global[coluna]
                    .round(2)
                )

if not simulacao_global.empty and "EAN" in df.columns:

    df["EAN"] = (
        df["EAN"]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.strip()
    )

    ganho_simulador = (
        simulacao_global[
            [
                "EAN",
                "Ganho_Potencial_Simulador"
            ]
        ]
        .rename(
            columns={
                "Ganho_Potencial_Simulador": "Ganho_Potencial"
            }
        )
    )

    df = df.drop(
        columns=[
            "Ganho_Potencial"
        ],
        errors="ignore"
    )

    df = df.merge(
        ganho_simulador,
        on="EAN",
        how="left"
    )

    df["Ganho_Potencial"] = (
        df["Ganho_Potencial"]
        .fillna(0)
    )

# --------------------------------------------------
# FILTROS
# --------------------------------------------------

st.sidebar.header("Filtros")

laboratorio = st.sidebar.multiselect(
    "Laboratório",
    sorted(
        df["Laboratório"]
        .dropna()
        .unique()
    )
)

familia = st.sidebar.multiselect(
    "Família",
    sorted(
        df["Família"]
        .dropna()
        .unique()
    )
)

curva = st.sidebar.multiselect(
    "Curva",
    sorted(
        df["CURVA"]
        .dropna()
        .unique()
    )
)

busca = st.sidebar.text_input(
    "Produto ou EAN"
)

# --------------------------------------------------
# FILTRAR
# --------------------------------------------------

df_filtrado = df.copy()

if laboratorio:

    df_filtrado = df_filtrado[
        df_filtrado["Laboratório"]
        .isin(laboratorio)
    ]

if familia:

    df_filtrado = df_filtrado[
        df_filtrado["Família"]
        .isin(familia)
    ]

if curva:

    df_filtrado = df_filtrado[
        df_filtrado["CURVA"]
        .isin(curva)
    ]

if busca:

    df_filtrado = df_filtrado[
        (
            df_filtrado["Produto"]
            .astype(str)
            .str.contains(
                busca,
                case=False,
                na=False
            )
        )
        |
        (
            df_filtrado["EAN"]
            .astype(str)
            .str.contains(
                busca,
                na=False
            )
        )
    ]

# --------------------------------------------------
# KPIS
# --------------------------------------------------

k1,k2,k3,k4,k5,k6 = st.columns(6)

k1.metric(
    "Produtos",
    len(df_filtrado)
)

k2.metric(
    "Margem Média",
    percentual_br(df_filtrado["Margem_%"].mean())
)

k3.metric(
    "Lucro Médio",
    moeda_br(df_filtrado["Lucro_Unitario"].mean())
)

k4.metric(
    "Ganho Potencial",
    moeda_br(df_filtrado["Ganho_Potencial"].sum())
)

k5.metric(
    "Laboratórios",
    df_filtrado["Laboratório"].nunique()
)

k6.metric(
    "Preço Médio",
    moeda_br(df_filtrado["Preco_Medio"].mean())
)

# --------------------------------------------------
# GRÁFICOS
# --------------------------------------------------

c1,c2 = st.columns(2)

with c1:

    rec = (
        df_filtrado["Recomendacao"]
        .value_counts()
        .reset_index()
    )

    rec.columns = [
        "Recomendacao",
        "Quantidade"
    ]

    # Remove SEM CUSTO do gráfico
    rec_grafico = rec[
        rec["Recomendacao"] != "SEM CUSTO"
    ].copy()

    fig = px.bar(
        rec_grafico,
        x="Recomendacao",
        y="Quantidade",
        text="Quantidade",
        title="Distribuição Recomendações"
    )

    fig.update_traces(
        textposition="outside"
    )

    st.plotly_chart(
        fig,
        width="stretch",
        key="grafico_recomendacoes"
    )

    # Ações recomendadas
    st.subheader(
        "📋 Ações Recomendadas"
    )

    acoes = {
        "SUBIR PREÇO URGENTE":
            "Produtos muito abaixo do mercado. Reajustar imediatamente.",
        "SUBIR PREÇO":
            "Produtos abaixo do mercado com oportunidade de ganho.",
        "MANTER":
            "Preço alinhado ao mercado. Monitorar concorrência.",
        "COMPETITIVO":
            "Preço agressivo. Avaliar margem e estratégia comercial.",
        "ANALISAR REDUÇÃO":
            "Preço elevado frente ao mercado. Revisar posicionamento.",
        "SEM CUSTO":
            "Produto sem custo cadastrado. Necessário saneamento do cadastro."
    }

    acoes_df = rec.copy()

    acoes_df["Ação Recomendada"] = (
        acoes_df["Recomendacao"]
        .map(acoes)
    )

    # Quadro interativo de recomendações
    selecao_recomendacao = st.dataframe(
        acoes_df[
            [
                "Recomendacao",
                "Quantidade",
                "Ação Recomendada"
            ]
        ],
        width="stretch",
        key="tabela_acoes_recomendadas",
        on_select="rerun",
        selection_mode="single-row"
    )

    recomendacao_selecionada = None

    try:

        linhas_selecionadas = (
            selecao_recomendacao
            .selection
            .rows
        )

        if linhas_selecionadas:

            recomendacao_selecionada = (
                acoes_df
                .iloc[linhas_selecionadas[0]]
                ["Recomendacao"]
            )

    except Exception:

        recomendacao_selecionada = None

    if recomendacao_selecionada is None:

        recomendacao_selecionada = st.selectbox(
            "Selecione a recomendação para detalhar",
            acoes_df["Recomendacao"].tolist(),
            key="select_recomendacao_detalhe"
        )

    st.subheader(
        f"🔎 Produtos da recomendação: {recomendacao_selecionada}"
    )

    produtos_recomendacao = df_filtrado[
        df_filtrado["Recomendacao"] == recomendacao_selecionada
    ].copy()

    if "EAN" in produtos_recomendacao.columns:

        produtos_recomendacao["EAN"] = (
            produtos_recomendacao["EAN"]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
        )

    # --------------------------------------------------
    # CRUZAR COM SIMULADOR PELO EAN
    # --------------------------------------------------

    if (
        "simulacao_global" in globals()
        and not simulacao_global.empty
        and "EAN" in produtos_recomendacao.columns
    ):

        simulador_base = simulacao_global.copy()

        simulador_base["EAN"] = (
            simulador_base["EAN"]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
        )

        cadastro_produtos = (
            produtos_recomendacao
            .drop_duplicates(
                subset=[
                    "EAN"
                ]
            )
            .copy()
        )

        colunas_cadastro = []

        for coluna in [
            "EAN",
            "Descricao_Unica",
            "Produto",
            "Laboratório",
            "Família",
            "CURVA",
            "Recomendacao",
            "Margem_%",
            "Lucro_Unitario",
            "Preco_Medio"
        ]:

            if coluna in cadastro_produtos.columns:
                colunas_cadastro.append(coluna)

        produtos_detalhe = simulador_base.merge(
            cadastro_produtos[colunas_cadastro],
            on="EAN",
            how="inner"
        )

        produtos_detalhe = produtos_detalhe.sort_values(
            "Ganho_Potencial_Simulador",
            ascending=False
        )

    else:

        produtos_detalhe = pd.DataFrame()

    if not produtos_detalhe.empty:

        # --------------------------------------------------
        # AJUSTES DE QUALIDADE DAS COLUNAS
        # --------------------------------------------------

        produtos_detalhe = produtos_detalhe.copy()

        # Se existir Produto_Simulador, usa como descrição principal quando Produto estiver vazio
        if "Produto_Simulador" in produtos_detalhe.columns:

            if "Produto" not in produtos_detalhe.columns:

                produtos_detalhe["Produto"] = produtos_detalhe["Produto_Simulador"]

            else:

                produtos_detalhe["Produto"] = (
                    produtos_detalhe["Produto"]
                    .fillna(produtos_detalhe["Produto_Simulador"])
                )

        # Trocar None/nan por vazio nas colunas textuais
        for coluna in [
            "Descricao_Unica",
            "Produto",
            "Laboratório",
            "Família",
            "CURVA",
            "Recomendacao"
        ]:

            if coluna in produtos_detalhe.columns:

                produtos_detalhe[coluna] = (
                    produtos_detalhe[coluna]
                    .fillna("")
                    .astype(str)
                    .replace(
                        {
                            "None": "",
                            "nan": "",
                            "NaN": ""
                        }
                    )
                )

        # Remove colunas cadastrais que vieram totalmente vazias
        for coluna in [
            "Laboratório",
            "Família",
            "CURVA",
            "Margem_%",
            "Lucro_Unitario"
        ]:

            if coluna in produtos_detalhe.columns:

                serie_limpa = (
                    produtos_detalhe[coluna]
                    .replace("", pd.NA)
                )

                if serie_limpa.isna().all():

                    produtos_detalhe = produtos_detalhe.drop(
                        columns=[
                            coluna
                        ]
                    )

        # --------------------------------------------------
        # COLUNAS PARA EXIBIÇÃO
        # --------------------------------------------------

        colunas_exibir = []

        for coluna in [
            "EAN",
            "Descricao_Unica",
            "Produto",
            "Laboratório",
            "Família",
            "CURVA",
            "Recomendacao",
            "Qtd_Vendida_Mes_Anterior",
            "Venda_Preco_Antigo",
            "Preco_Atual",
            "Preco_Sugerido_Mercado",
            "Venda_Projetada_Preco_Sugerido",
            "Ganho_Unitario",
            "Ganho_Potencial_Simulador",
            "Margem_%",
            "Lucro_Unitario",
            "Preco_Medio"
        ]:

            if coluna in produtos_detalhe.columns:
                colunas_exibir.append(coluna)

        produtos_exibir = produtos_detalhe[colunas_exibir].copy()

        # --------------------------------------------------
        # FORMATAR PADRÃO BRASIL
        # --------------------------------------------------

        for coluna in [
            "Venda_Preco_Antigo",
            "Preco_Atual",
            "Preco_Sugerido_Mercado",
            "Venda_Projetada_Preco_Sugerido",
            "Ganho_Unitario",
            "Ganho_Potencial_Simulador",
            "Lucro_Unitario",
            "Preco_Medio"
        ]:

            if coluna in produtos_exibir.columns:
                produtos_exibir[coluna] = produtos_exibir[coluna].apply(moeda_br)

        if "Margem_%" in produtos_exibir.columns:
            produtos_exibir["Margem_%"] = produtos_exibir["Margem_%"].apply(percentual_br)

        if "Qtd_Vendida_Mes_Anterior" in produtos_exibir.columns:
            produtos_exibir["Qtd_Vendida_Mes_Anterior"] = (
                produtos_exibir["Qtd_Vendida_Mes_Anterior"]
                .apply(numero_br)
            )

        # Limpeza final para não exibir None/nan
        produtos_exibir = (
            produtos_exibir
            .replace(
                {
                    "None": "",
                    "nan": "",
                    "NaN": "",
                    "R$ nan": "",
                    "nan%": ""
                }
            )
            .fillna("")
        )

        st.dataframe(
            produtos_exibir,
            width="stretch"
        )

        # --------------------------------------------------
        # EXPORTAÇÃO DA RECOMENDAÇÃO
        # --------------------------------------------------

        exportar_recomendacao = produtos_detalhe[colunas_exibir].copy()

        for coluna in [
            "Venda_Preco_Antigo",
            "Preco_Atual",
            "Preco_Sugerido_Mercado",
            "Venda_Projetada_Preco_Sugerido",
            "Ganho_Unitario",
            "Ganho_Potencial_Simulador",
            "Lucro_Unitario",
            "Preco_Medio"
        ]:

            if coluna in exportar_recomendacao.columns:
                exportar_recomendacao[coluna] = exportar_recomendacao[coluna].apply(moeda_br)

        if "Margem_%" in exportar_recomendacao.columns:
            exportar_recomendacao["Margem_%"] = exportar_recomendacao["Margem_%"].apply(percentual_br)

        if "Qtd_Vendida_Mes_Anterior" in exportar_recomendacao.columns:
            exportar_recomendacao["Qtd_Vendida_Mes_Anterior"] = (
                exportar_recomendacao["Qtd_Vendida_Mes_Anterior"]
                .apply(numero_br)
            )

        exportar_recomendacao = (
            exportar_recomendacao
            .replace(
                {
                    "None": "",
                    "nan": "",
                    "NaN": "",
                    "R$ nan": "",
                    "nan%": ""
                }
            )
            .fillna("")
        )

        csv_recomendacao = (
            exportar_recomendacao
            .to_csv(
                index=False,
                sep=";"
            )
            .encode("utf-8-sig")
        )

        st.download_button(
            "📥 Exportar produtos da recomendação",
            csv_recomendacao,
            f"produtos_{recomendacao_selecionada.lower().replace(' ', '_')}.csv",
            "text/csv",
            key="exportar_recomendacao"
        )

    else:

        st.warning(
            "Não há produtos dessa recomendação com dados completos no Simulador. "
            "Isso ocorre quando o EAN não existe na venda da rede ou não teve venda no período."
        )

with c2:

    top_lab = (
        df_filtrado
        .groupby("Laboratório")
        ["Ganho_Potencial"]
        .sum()
        .reset_index()
        .sort_values(
            "Ganho_Potencial",
            ascending=False
        )
        .head(15)
    )

    fig = px.bar(
        top_lab,
        x="Laboratório",
        y="Ganho_Potencial",
        title="Top Laboratórios"
    )

    st.plotly_chart(
        fig,
        width="stretch",
        key="top_laboratorios"
    )

# --------------------------------------------------
# CURVA ABC
# --------------------------------------------------

st.subheader(
    "📈 Curva ABC"
)

abc = curva_abc(df_filtrado)

# --------------------------------------------------
# MENOR PREÇO, REDE, FARMÁCIA E DATA DA PESQUISA
# --------------------------------------------------

if (
    not abc.empty
    and not historico.empty
    and "Descricao_Unica" in historico.columns
    and "Preço (R$)" in historico.columns
    and "Farmácia" in historico.columns
):

    hist_abc = historico.copy()

    if "Rede" not in hist_abc.columns:
        hist_abc["Rede"] = (
            hist_abc["Farmácia"]
            .apply(identificar_rede)
        )

    hist_abc["Preço (R$)"] = pd.to_numeric(
        hist_abc["Preço (R$)"],
        errors="coerce"
    )

    if "Data Emissão" in hist_abc.columns:

        hist_abc["Data Emissão"] = pd.to_datetime(
            hist_abc["Data Emissão"],
            errors="coerce",
            dayfirst=True
        )

    else:

        hist_abc["Data Emissão"] = pd.NaT

    hist_abc = hist_abc.dropna(
        subset=[
            "Descricao_Unica",
            "Preço (R$)"
        ]
    )

    idx_menor = (
        hist_abc
        .groupby("Descricao_Unica")
        ["Preço (R$)"]
        .idxmin()
    )

    menor_preco_produto = (
        hist_abc
        .loc[
            idx_menor,
            [
                "Descricao_Unica",
                "Preço (R$)",
                "Rede",
                "Farmácia",
                "Data Emissão"
            ]
        ]
        .rename(
            columns={
                "Descricao_Unica": "Produto",
                "Preço (R$)": "Menor_Preco",
                "Rede": "Rede_Menor_Preco",
                "Farmácia": "Farmacia_Menor_Preco",
                "Data Emissão": "Data_Pesquisa"
            }
        )
    )

    abc = abc.merge(
        menor_preco_produto,
        on="Produto",
        how="left"
    )

# --------------------------------------------------
# GARANTIR COLUNAS
# --------------------------------------------------

for coluna in [
    "Menor_Preco",
    "Rede_Menor_Preco",
    "Farmacia_Menor_Preco",
    "Data_Pesquisa"
]:

    if coluna not in abc.columns:
        abc[coluna] = None

# --------------------------------------------------
# FORMATAÇÃO
# --------------------------------------------------

if "Ganho_Potencial" in abc.columns:

    abc["Ganho_Potencial"] = pd.to_numeric(
        abc["Ganho_Potencial"],
        errors="coerce"
    ).round(2)

if "Menor_Preco" in abc.columns:

    abc["Menor_Preco"] = pd.to_numeric(
        abc["Menor_Preco"],
        errors="coerce"
    ).round(2)

if "Perc_Acum" in abc.columns:

    abc["Perc_Acum"] = (
        pd.to_numeric(
            abc["Perc_Acum"],
            errors="coerce"
        )
        * 100
    ).round(2)

# --------------------------------------------------
# EXIBIÇÃO BRASIL
# --------------------------------------------------

abc_exibir = abc.copy()

if "Ganho_Potencial" in abc_exibir.columns:
    abc_exibir["Ganho_Potencial"] = (
        abc_exibir["Ganho_Potencial"]
        .apply(moeda_br)
    )

if "Menor_Preco" in abc_exibir.columns:
    abc_exibir["Menor_Preco"] = (
        abc_exibir["Menor_Preco"]
        .apply(moeda_br)
    )

if "Perc_Acum" in abc_exibir.columns:
    abc_exibir["Perc_Acum"] = (
        abc_exibir["Perc_Acum"]
        .apply(percentual_br)
    )

if "Data_Pesquisa" in abc_exibir.columns:
    abc_exibir["Data_Pesquisa"] = (
        pd.to_datetime(
            abc_exibir["Data_Pesquisa"],
            errors="coerce",
            dayfirst=True
        )
        .dt.strftime("%d/%m/%Y")
        .fillna("")
    )

st.dataframe(
    abc_exibir[
        [
            "Produto",
            "Ganho_Potencial",
            "Menor_Preco",
            "Rede_Menor_Preco",
            "Farmacia_Menor_Preco",
            "Data_Pesquisa",
            "Perc_Acum",
            "ABC"
        ]
    ],
    width="stretch"
)

# --------------------------------------------------
# TOP GANHOS
# --------------------------------------------------

st.subheader(
    "💰 Top Oportunidades"
)

top_oportunidades = (
    df_filtrado
    .sort_values(
        "Ganho_Potencial",
        ascending=False
    )
    .head(50)
    .copy()
)

for coluna in [
    "Ganho_Potencial",
    "Lucro_Unitario",
    "Preco_Medio",
    "Margem_%"
]:

    if coluna in top_oportunidades.columns:

        if coluna == "Margem_%":
            top_oportunidades[coluna] = top_oportunidades[coluna].apply(percentual_br)
        else:
            top_oportunidades[coluna] = top_oportunidades[coluna].apply(moeda_br)

st.dataframe(
    top_oportunidades,
    width="stretch"
)

# --------------------------------------------------
# HEATMAP
# --------------------------------------------------

st.subheader(
    "🔥 Heatmap"
)

heat = pd.pivot_table(
    df_filtrado,
    values="Ganho_Potencial",
    index="Família",
    columns="Laboratório",
    aggfunc="sum"
).fillna(0)

fig = px.imshow(
    heat,
    aspect="auto"
)

st.plotly_chart(
    fig,
    width="stretch",
    key="heatmap"
)

# --------------------------------------------------
# HISTÓRICO
# --------------------------------------------------

if not historico.empty:

    st.subheader("📈 Evolução Histórica")

    # Garantir coluna Descricao_Unica
    if "Descricao_Unica" not in historico.columns:

        if "Produto" in historico.columns:
            historico["Descricao_Unica"] = historico["Produto"]
        else:
            historico["Descricao_Unica"] = "SEM DESCRIÇÃO"

    produtos = (
        historico["Descricao_Unica"]
        .value_counts()
        .index
        .tolist()
    )

    ean_padrao = "78911222"

    indice_padrao = 0

    for i, item in enumerate(produtos):

        if str(item).startswith(ean_padrao):
            indice_padrao = i
            break

    produto = st.selectbox(
        "Produto",
        produtos,
        index=indice_padrao,
        key="historico_produto"
    )

    ean_selecionado_historico = (
        str(produto)
        .split(" - ")[0]
        .strip()
    )

    if "EAN" not in historico.columns and "EAN (GTIN)" in historico.columns:

        historico["EAN"] = historico["EAN (GTIN)"]

    if "EAN" in historico.columns:

        historico["EAN"] = (
            historico["EAN"]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
        )

        hist = historico[
            historico["EAN"] == ean_selecionado_historico
        ]

    else:

        hist = historico[
            historico["Descricao_Unica"] == produto
        ]

    if (
        "Data Emissão" in hist.columns
        and
        "Preço (R$)" in hist.columns
    ):

        fig = px.line(
            hist,
            x="Data Emissão",
            y="Preço (R$)",
            color="Farmácia"
        )

        st.plotly_chart(
            fig,
            width="stretch",
            key="historico"
        )

# --------------------------------------------------
# MAPA
# --------------------------------------------------

if (
    not historico.empty
    and
    "lat" in historico.columns
    and
    "lon" in historico.columns
):

    st.subheader(
        "🗺️ Mapa Farmácias"
    )

    mapa_df = historico.copy()

    mapa_df["lat"] = pd.to_numeric(
        mapa_df["lat"],
        errors="coerce"
    )

    mapa_df["lon"] = pd.to_numeric(
        mapa_df["lon"],
        errors="coerce"
    )

    mapa_df = mapa_df.dropna(
        subset=[
            "lat",
            "lon"
        ]
    )

    mapa_df["Tipo_Loja"] = "Concorrência"

    if "Farmácia" in mapa_df.columns:

        nome_farmacia = (
            mapa_df["Farmácia"]
            .astype(str)
            .str.upper()
        )

        mapa_df.loc[
            nome_farmacia.str.contains(
                "ZANOL E THOMAZ LTDA",
                na=False
            ),
            "Tipo_Loja"
        ] = "Zanol e Thomaz"

        mapa_df.loc[
            nome_farmacia.str.contains(
                "TRIANGULO DROGARIA LTDA",
                na=False
            ),
            "Tipo_Loja"
        ] = "Triangulo Drogaria"

    hover_cols = []

    for coluna in [
        "Farmácia",
        "Produto",
        "Preço (R$)",
        "Rede",
        "Data Emissão"
    ]:

        if coluna in mapa_df.columns:
            hover_cols.append(coluna)

    fig_mapa = px.scatter_mapbox(
        mapa_df,
        lat="lat",
        lon="lon",
        color="Tipo_Loja",
        color_discrete_map={
            "Concorrência": "red",
            "Zanol e Thomaz": "yellow",
            "Triangulo Drogaria": "blue"
        },
        hover_name="Farmácia" if "Farmácia" in mapa_df.columns else None,
        hover_data=hover_cols,
        zoom=11,
        height=550
    )

    fig_mapa.update_layout(
        mapbox_style="carto-darkmatter",
        margin={
            "r": 0,
            "t": 0,
            "l": 0,
            "b": 0
        },
        legend_title_text="Tipo de Loja"
    )

    st.plotly_chart(
        fig_mapa,
        width="stretch",
        key="mapa_farmacias_cores"
    )

# --------------------------------------------------
# MONITORAMENTO POR REDE
# --------------------------------------------------

if not historico.empty and "Farmácia" in historico.columns:

    st.subheader("🏪 Monitoramento por Rede")

    historico["Rede"] = (
        historico["Farmácia"]
        .apply(identificar_rede)
    )

    rede_df = (
        historico
        .groupby("Rede")
        ["Preço (R$)"]
        .mean()
        .reset_index()
    )

    fig = px.bar(
        rede_df,
        x="Rede",
        y="Preço (R$)"
    )

    st.plotly_chart(
        fig,
        width="stretch",
        key="monitoramento_rede"
    )

# --------------------------------------------------
# RANKING CONCORRENTES
# --------------------------------------------------

if not historico.empty:

    st.subheader(
        "🏆 Ranking Concorrentes"
    )

    ranking = (
        historico
        .groupby("Farmácia")
        ["Preço (R$)"]
        .mean()
        .reset_index()
        .sort_values(
            "Preço (R$)"
        )
    )

    ranking_exibir = ranking.copy()

    if "Preço (R$)" in ranking_exibir.columns:
        ranking_exibir["Preço (R$)"] = ranking_exibir["Preço (R$)"].apply(moeda_br)

    st.dataframe(
        ranking_exibir,
        width="stretch"
    )

# --------------------------------------------------

# FAMÍLIAS

# --------------------------------------------------

st.subheader(
"💊 Famílias"
)

familias = (
df_filtrado
.groupby("Família")
["Ganho_Potencial"]
.sum()
.reset_index()
)

fig = px.bar(
familias
.sort_values(
"Ganho_Potencial",
ascending=False
)
.head(20),
x="Família",
y="Ganho_Potencial"
)

st.plotly_chart(
    fig,
    width="stretch",
    key="familias"
)

# --------------------------------------------------
# LABORATÓRIOS
# --------------------------------------------------

st.subheader(
    "🏭 Laboratórios"
)

laboratorios = (
    df_filtrado
    .groupby("Laboratório")
    .agg({
        "Ganho_Potencial": "sum",
        "Margem_%": "mean"
    })
    .reset_index()
)

laboratorios_exibir = (
    laboratorios
    .sort_values(
        "Ganho_Potencial",
        ascending=False
    )
    .copy()
)

if "Ganho_Potencial" in laboratorios_exibir.columns:
    laboratorios_exibir["Ganho_Potencial"] = laboratorios_exibir["Ganho_Potencial"].apply(moeda_br)

if "Margem_%" in laboratorios_exibir.columns:
    laboratorios_exibir["Margem_%"] = laboratorios_exibir["Margem_%"].apply(percentual_br)

st.dataframe(
    laboratorios_exibir,
    width="stretch"
)

# --------------------------------------------------
# CURVA ABC FINANCEIRA
# --------------------------------------------------

if not compra.empty:

    st.subheader(
        "📦 Curva ABC Financeira"
    )

    # Remove colunas vazias do Excel
    compra = compra.loc[
        :,
        ~compra.columns.astype(str).str.contains("^Unnamed")
    ]

    # Ordena pelo maior faturamento
    compra = compra.sort_values(
        "Valor_Liquido",
        ascending=False
    )

    # Calcula participação
    total = compra["Valor_Liquido"].sum()

    compra["Participacao"] = (
        compra["Valor_Liquido"] / total
    )

    # Acumulado
    compra["Acumulado"] = (
        compra["Participacao"].cumsum()
    )

    # Classe ABC
    compra["Classe"] = "C"

    compra.loc[
        compra["Acumulado"] <= 0.80,
        "Classe"
    ] = "A"

    compra.loc[
        (
            compra["Acumulado"] > 0.80
        )
        &
        (
            compra["Acumulado"] <= 0.95
        ),
        "Classe"
    ] = "B"

    # Formatação %
    compra["Participacao"] = (
        compra["Participacao"] * 100
    ).round(2)

    compra["Acumulado"] = (
        compra["Acumulado"] * 100
    ).round(2)

    # Tabela
    compra_exibir = compra[
        [
            "Marca",
            "Valor_Liquido",
            "Participacao",
            "Acumulado",
            "Classe"
        ]
    ].head(100).copy()

    compra_exibir["Valor_Liquido"] = (
        compra_exibir["Valor_Liquido"]
        .apply(moeda_br)
    )

    compra_exibir["Participacao"] = (
        compra_exibir["Participacao"]
        .apply(percentual_br)
    )

    compra_exibir["Acumulado"] = (
        compra_exibir["Acumulado"]
        .apply(percentual_br)
    )

    st.dataframe(
        compra_exibir,
        width="stretch"
    )

    # Gráfico
    fig = px.bar(
        compra.head(20),
        x="Marca",
        y="Valor_Liquido",
        color="Classe",
        title="Top 20 Marcas - Curva ABC"
    )

    st.plotly_chart(
        fig,
        width="stretch",
        key="abc_financeira"
    )

# --------------------------------------------------

# SCORE EIROX

# --------------------------------------------------

st.subheader(
"🤖 Score Eirox"
)

score = round(
(
df_filtrado["Margem_%"].mean()
* 0.6
)
+
(
df_filtrado["Ganho_Potencial"].sum()
/ 1000
)
* 0.4
)

st.metric(
"Score Pricing",
score
)


# --------------------------------------------------
# COMPARATIVO DE REDES
# --------------------------------------------------

if (
    not historico.empty
    and "Produto" in historico.columns
    and "Farmácia" in historico.columns
    and "Preço (R$)" in historico.columns
):

    st.subheader("📊 Comparativo de Redes")

    if "Rede" not in historico.columns:
        historico["Rede"] = historico["Farmácia"].apply(
            identificar_rede
        )

    if "EAN" not in historico.columns and "EAN (GTIN)" in historico.columns:
        historico["EAN"] = historico["EAN (GTIN)"]

    if "EAN" in historico.columns:
        historico["EAN"] = (
            historico["EAN"]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
        )

    produtos = (
        historico["Descricao_Unica"]
        .dropna()
        .drop_duplicates()
        .astype(str)
        .sort_values()
        .tolist()
    )

    ean_padrao = "78911222"

    indice_padrao = 0

    for i, item in enumerate(produtos):

        if str(item).startswith(ean_padrao):
            indice_padrao = i
            break

    produto = st.selectbox(
        "Produto",
        produtos,
        index=indice_padrao,
        key="comparativo_produto"
    )

    ean_selecionado = (
        str(produto)
        .split(" - ")[0]
        .strip()
    )

    if "EAN" in historico.columns:

        comp_df = historico[
            historico["EAN"] == ean_selecionado
        ].copy()

    else:

        comp_df = historico[
            historico["Descricao_Unica"] == produto
        ].copy()

    ranking = (
        comp_df[
            [
                "Rede",
                "Farmácia",
                "Preço (R$)"
            ]
        ]
        .copy()
    )

    ranking["Preço (R$)"] = pd.to_numeric(
        ranking["Preço (R$)"],
        errors="coerce"
    )

    ranking = ranking.dropna(
        subset=[
            "Preço (R$)"
        ]
    )

    ranking = (
        ranking
        .groupby(
            [
                "Rede",
                "Farmácia"
            ],
            as_index=False
        )
        ["Preço (R$)"]
        .mean()
    )

    ranking["Preço (R$)"] = (
        ranking["Preço (R$)"]
        .round(2)
    )

    menor_mercado = round(
        ranking["Preço (R$)"]
        .min(),
        2
    )

    ranking["Menor Mercado"] = menor_mercado

    ranking["Dif R$"] = (
        ranking["Preço (R$)"]
        - menor_mercado
    ).round(2)

    ranking["Dif %"] = (
        ranking["Dif R$"]
        / menor_mercado
        * 100
    ).round(2)

    ranking["Status"] = ranking["Dif R$"].apply(
        lambda x:
        "LÍDER"
        if abs(x) < 0.01
        else "ACIMA MERCADO"
    )

    ranking["Loja"] = (
        ranking["Rede"].astype(str)
        + " - "
        + ranking["Farmácia"].astype(str)
    )

    ranking = ranking.sort_values(
        "Preço (R$)",
        ascending=True
    )

    ranking_exibir = ranking.copy()

    for coluna in [
        "Preço (R$)",
        "Menor Mercado",
        "Dif R$"
    ]:

        if coluna in ranking_exibir.columns:
            ranking_exibir[coluna] = ranking_exibir[coluna].apply(moeda_br)

    if "Dif %" in ranking_exibir.columns:
        ranking_exibir["Dif %"] = ranking_exibir["Dif %"].apply(percentual_br)

    st.dataframe(
        ranking_exibir[
            [
                "Rede",
                "Farmácia",
                "Preço (R$)",
                "Menor Mercado",
                "Dif R$",
                "Dif %",
                "Status"
            ]
        ],
        width="stretch"
    )

    fig = px.bar(
        ranking,
        x="Loja",
        y="Preço (R$)",
        color="Status",
        text="Preço (R$)",
        title=f"Comparativo de Preço por Loja - {produto}"
    )

    fig.update_traces(
        texttemplate="R$ %{text:.2f}",
        textposition="outside"
    )

    fig.update_layout(
        xaxis_title="Loja",
        yaxis_title="Preço (R$)"
    )

    st.plotly_chart(
        fig,
        width="stretch",
        key="comparativo_rede"
    )

    st.subheader(
        "📋 Produtos Filtrados"
    )

    produtos_filtrados = (
        comp_df[
            [
                "Descricao_Unica",
                "Produto",
                "Rede",
                "Farmácia",
                "Preço (R$)"
            ]
        ]
        .copy()
    )

    produtos_filtrados["Preço (R$)"] = pd.to_numeric(
        produtos_filtrados["Preço (R$)"],
        errors="coerce"
    ).round(2)

    produtos_filtrados = produtos_filtrados.sort_values(
        "Preço (R$)",
        ascending=True
    )

    produtos_filtrados_exibir = produtos_filtrados.copy()

    if "Preço (R$)" in produtos_filtrados_exibir.columns:
        produtos_filtrados_exibir["Preço (R$)"] = (
            produtos_filtrados_exibir["Preço (R$)"]
            .apply(moeda_br)
        )

    st.dataframe(
        produtos_filtrados_exibir,
        width="stretch"
    )


# --------------------------------------------------
# SIMULADOR DE GANHO COM REAJUSTE
# --------------------------------------------------

st.subheader(
    "💵 Simulador de Ganho com Ajuste de Preço"
)

if not simulacao_global.empty:

    simulacao = simulacao_global.copy()

    if "Produto_Simulador" in simulacao.columns:
        simulacao = simulacao.rename(
            columns={
                "Produto_Simulador": "Produto"
            }
        )

    simulacao = simulacao.sort_values(
        "Ganho_Potencial_Simulador",
        ascending=False
    )

    k1, k2, k3, k4 = st.columns(4)

    k1.metric(
        "Produtos com Oportunidade",
        len(simulacao)
    )

    k2.metric(
        "Venda Preço Antigo",
        moeda_br(simulacao["Venda_Preco_Antigo"].sum())
    )

    k3.metric(
        "Venda com Preço Sugerido",
        moeda_br(simulacao["Venda_Projetada_Preco_Sugerido"].sum())
    )

    k4.metric(
        "Ganho Total",
        moeda_br(simulacao["Ganho_Potencial_Simulador"].sum())
    )

    colunas_exibir = [
        "EAN"
    ]

    if "Produto" in simulacao.columns:
        colunas_exibir.append("Produto")

    colunas_exibir += [
        "Qtd_Vendida_Mes_Anterior",
        "Venda_Preco_Antigo",
        "Preco_Atual",
        "Preco_Sugerido_Mercado",
        "Venda_Projetada_Preco_Sugerido",
        "Ganho_Unitario",
        "Ganho_Potencial_Simulador"
    ]

    simulacao_exibir = simulacao[colunas_exibir].copy()

    for coluna in [
        "Venda_Preco_Antigo",
        "Preco_Atual",
        "Preco_Sugerido_Mercado",
        "Venda_Projetada_Preco_Sugerido",
        "Ganho_Unitario",
        "Ganho_Potencial_Simulador"
    ]:

        if coluna in simulacao_exibir.columns:
            simulacao_exibir[coluna] = simulacao_exibir[coluna].apply(moeda_br)

    if "Qtd_Vendida_Mes_Anterior" in simulacao_exibir.columns:
        simulacao_exibir["Qtd_Vendida_Mes_Anterior"] = (
            simulacao_exibir["Qtd_Vendida_Mes_Anterior"]
            .apply(numero_br)
        )

    st.dataframe(
        simulacao_exibir,
        width="stretch"
    )

    fig = px.bar(
        simulacao.head(20),
        x="Produto" if "Produto" in simulacao.columns else "EAN",
        y="Ganho_Potencial_Simulador",
        title="Top 20 Produtos com Maior Ganho Projetado"
    )

    st.plotly_chart(
        fig,
        width="stretch",
        key="simulador_ganho_reajuste"
    )

else:

    st.warning(
        "As bases necessárias ainda não possuem dados compatíveis para simulação."
    )

    if not venda_rede.empty:
        st.write("Colunas encontradas em VENDA_FINAL_TESTE:")
        st.write(venda_rede.columns.tolist())

    if not historico.empty:
        st.write("Colunas encontradas em VENDA_TESTE:")
        st.write(historico.columns.tolist())


# --------------------------------------------------
# EXPORTAÇÃO
# --------------------------------------------------

st.subheader(
    "📥 Exportação"
)

csv = (
    df_filtrado
    .to_csv(index=False)
    .encode("utf-8")
)

st.download_button(
    "Baixar CSV",
    csv,
    "pricing_eirox.csv",
    "text/csv"
)