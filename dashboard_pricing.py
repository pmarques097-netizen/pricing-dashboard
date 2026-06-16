import streamlit as st
import streamlit.components.v1 as components
import os
import re
import zipfile
import shutil
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import hashlib
import time
import csv
import io
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

pio.templates.default = "plotly_dark"


st.markdown(
    """
    <style>
        .block-container {
            max-width: 100% !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
        }

        div[data-testid="stDataFrame"] {
            width: 100% !important;
        }

        div[data-testid="stDataFrame"] > div {
            width: 100% !important;
        }
    
}

</style>
    """,
    unsafe_allow_html=True
)



st.markdown(
    """
    <style>
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0E2A4F 0%, #071A33 100%);
        }

        section[data-testid="stSidebar"] .block-container {
            padding-top: 1.5rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }

        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span {
            color: #FFFFFF !important;
        }

        .sidebar-card {
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.14);
            border-radius: 14px;
            padding: 14px 14px;
            margin-bottom: 14px;
        }

        .sidebar-title {
            font-size: 18px;
            font-weight: 800;
            color: #FFFFFF;
            margin-bottom: 4px;
        }

        .sidebar-subtitle {
            font-size: 12px;
            color: #BFD7FF;
            margin-bottom: 0px;
        }

        .sidebar-user {
            font-size: 13px;
            color: #FFFFFF;
            margin: 2px 0px;
        }

        .sidebar-pill {
            display: inline-block;
            background: rgba(44, 160, 255, 0.22);
            border: 1px solid rgba(44, 160, 255, 0.45);
            color: #D8ECFF;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            margin-top: 6px;
        }

        .sidebar-section {
            font-size: 12px;
            font-weight: 800;
            letter-spacing: .08em;
            text-transform: uppercase;
            color: #9FC7FF;
            margin-top: 18px;
            margin-bottom: 8px;
        }

        div[data-testid="stSidebarUserContent"] hr {
            border-color: rgba(255,255,255,0.18);
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label {
            background: rgba(255,255,255,0.06);
            border-radius: 10px;
            padding: 7px 9px;
            margin-bottom: 5px;
            border: 1px solid rgba(255,255,255,0.08);
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
            background: rgba(255,255,255,0.12);
            border-color: rgba(255,255,255,0.20);
        }

        section[data-testid="stSidebar"] button {
            border-radius: 10px !important;
            border: 1px solid rgba(255,255,255,0.20) !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# --------------------------------------------------
# VERSÃO DE DEPURAÇÃO / CONTROLE DE DEPLOY
# --------------------------------------------------

VERSAO_APP = "v1.40.2-br-valores-score-claro-colunas-v1"

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


def moeda_br_kpi(valor):

    """
    Formata moeda para KPI sem cortar o valor no card.
    Mantém o padrão brasileiro e usa MM quando o valor passa de 1 milhão.
    """

    try:
        if pd.isna(valor):
            return ""

        valor = float(valor)

        if abs(valor) >= 1_000_000:
            return (
                f"R$ {valor / 1_000_000:,.2f} MM"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )

        return moeda_br(valor)

    except Exception:
        return moeda_br(valor)


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


# --------------------------------------------------
# FORMATAÇÃO BRASILEIRA GLOBAL PARA EXIBIÇÃO
# --------------------------------------------------

def inteiro_br(valor):

    try:
        if pd.isna(valor):
            return ""
        return f"{float(valor):,.0f}".replace(",", ".")
    except Exception:
        return ""


def data_br(valor):

    try:
        if pd.isna(valor):
            return ""
        data = pd.to_datetime(valor, errors="coerce")
        if pd.isna(data):
            return str(valor)
        return data.strftime("%d/%m/%Y")
    except Exception:
        return str(valor) if valor is not None else ""


def _eirox_tipo_coluna_br(nome_coluna):
    nome = str(nome_coluna).lower().strip()

    if any(t in nome for t in [
        "margem", "percent", "particip", "%", "variação", "variacao",
        "rentabilidade", "share", "taxa"
    ]):
        return "percentual"

    if any(t in nome for t in [
        "preço", "preco", "custo", "valor", "faturamento", "venda",
        "receita", "lucro", "ganho", "potencial", "captura", "ticket",
        "despesa", "saldo", "total r$", "r$", "recomendado", "sugerido"
    ]):
        return "moeda"

    if any(t in nome for t in [
        "data", "dt ", "dt_", "modificado", "criado", "atualização", "atualizacao"
    ]):
        return "data"

    if any(t in nome for t in [
        "qtd", "qtde", "quantidade", "unidades", "estoque", "itens",
        "produtos", "skus", "ranking", "posição", "posicao", "arquivos", "registros"
    ]):
        return "inteiro"

    if "score" in nome or "índice" in nome or "indice" in nome:
        return "numero"

    return "texto"


def formatar_dataframe_br(base):
    """
    Formata uma cópia do DataFrame apenas para exibição no padrão brasileiro.
    Não altera a base original usada nos cálculos.
    """

    if not isinstance(base, pd.DataFrame) or base.empty:
        return base

    df_view = base.copy()

    # Nomes mais claros para o usuário final.
    renomear = {
        "Ganho_Potencial": "Potencial de Captura",
        "Ganho_Potencial_Final": "Potencial de Captura Final",
        "Ganho_Potencial_Atualizado": "Potencial de Captura Atualizado",
        "Ganho_Potencial_Simulador": "Potencial de Captura Simulado",
        "Margem_%": "Rentabilidade Atual",
        "Margem_Media": "Rentabilidade Atual",
        "Score_Eirox": "Índice de Oportunidade Eirox",
        "Preco_Atual": "Preço Atual",
        "Preco_Sugerido_Mercado": "Preço Máximo Competitivo",
        "Rede_Preco_Maximo_Competitivo": "Rede Preço Máximo Competitivo",
        "Data_Preco_Maximo_Competitivo": "Data Preço Máximo Competitivo",
        "Menor_Preco": "Menor Preço",
        "Rede_Menor_Preco": "Rede Menor Preço",
        "Data_Menor_Preco": "Data Menor Preço",
        "Preco_Recomendado": "Preço Recomendado",
        "Qtd_Vendida_Mes_Anterior": "Qtd Vendida Mês Anterior"
    }

    df_view = df_view.rename(columns={c: renomear.get(c, c) for c in df_view.columns})

    for coluna in df_view.columns:
        tipo = _eirox_tipo_coluna_br(coluna)

        if tipo == "moeda":
            s_num = pd.to_numeric(df_view[coluna], errors="coerce")
            if s_num.notna().any():
                df_view[coluna] = s_num.apply(moeda_br)

        elif tipo == "percentual":
            s_num = pd.to_numeric(df_view[coluna], errors="coerce")
            if s_num.notna().any():
                df_view[coluna] = s_num.apply(percentual_br)

        elif tipo == "inteiro":
            s_num = pd.to_numeric(df_view[coluna], errors="coerce")
            if s_num.notna().any():
                df_view[coluna] = s_num.apply(inteiro_br)

        elif tipo == "numero":
            s_num = pd.to_numeric(df_view[coluna], errors="coerce")
            if s_num.notna().any():
                df_view[coluna] = s_num.apply(numero_br)

        elif tipo == "data":
            # Só formata quando parecer data de verdade.
            convertido = pd.to_datetime(df_view[coluna], errors="coerce")
            if convertido.notna().any():
                df_view[coluna] = convertido.dt.strftime("%d/%m/%Y")

    return df_view


def valor_metrica_br(label, valor):
    """Padroniza KPIs no formato brasileiro conforme o tipo do indicador."""

    if isinstance(valor, str):
        return valor

    try:
        nome = str(label).lower()

        if any(t in nome for t in ["preço", "preco", "custo", "valor", "faturamento", "venda", "lucro", "ganho", "potencial", "captura", "ticket", "receita", "despesa", "saldo"]):
            return moeda_br(valor)

        if any(t in nome for t in ["margem", "rentabilidade", "particip", "%", "percent", "taxa"]):
            return percentual_br(valor)

        if any(t in nome for t in ["produtos", "itens", "qtd", "quantidade", "estoque", "arquivos", "registros", "usuários", "usuarios"]):
            return inteiro_br(valor)

        if "score" in nome or "índice" in nome or "indice" in nome:
            return numero_br(valor)

        return numero_br(valor) if isinstance(valor, (int, float, np.integer, np.floating)) else valor

    except Exception:
        return valor


def aplicar_formatacao_brasileira_streamlit():
    """
    Intercepta st.dataframe e st.metric para exibir números, dinheiro,
    percentuais e datas no padrão brasileiro em todo o dashboard.
    """

    if getattr(st, "_eirox_formatacao_br_aplicada", False):
        return

    st._eirox_dataframe_original = st.dataframe
    st._eirox_metric_original = st.metric

    def dataframe_br(data=None, *args, **kwargs):
        try:
            if isinstance(data, pd.DataFrame):
                data = formatar_dataframe_br(data)
        except Exception:
            pass
        return st._eirox_dataframe_original(data, *args, **kwargs)

    def metric_br(label, value, delta=None, *args, **kwargs):
        try:
            value = valor_metrica_br(label, value)
            if delta is not None and not isinstance(delta, str):
                delta = valor_metrica_br(label, delta)
        except Exception:
            pass
        return st._eirox_metric_original(label, value, delta, *args, **kwargs)

    st.dataframe = dataframe_br
    st.metric = metric_br
    st._eirox_formatacao_br_aplicada = True


aplicar_formatacao_brasileira_streamlit()



def explicacao_calculo(titulo, itens):
    """
    Exibe, no painel, a explicação visual dos cálculos usados em cada visão.
    Mantém a regra de negócio transparente para o usuário final.
    """

    try:
        if not isinstance(itens, (list, tuple)):
            itens = [str(itens)]

        lista_html = "".join(
            f"<li>{str(item)}</li>"
            for item in itens
            if str(item).strip()
        )

        st.markdown(
            f"""
            <div class="eirox-card">
                <div class="eirox-section-title">Como calcular</div>
                <h4 style="margin-top:0;color:#F6FAFF!important;">{titulo}</h4>
                <ul style="margin-bottom:0;color:#BFD7FF;line-height:1.55;">
                    {lista_html}
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )
    except Exception:
        pass


def propagar_ganho_potencial(base):
    """
    Garante que todos os indicadores usem o mesmo Ganho_Potencial.
    """

    if not isinstance(base, pd.DataFrame) or base.empty:
        return base

    base = base.copy()

    if "Ganho_Potencial" not in base.columns:
        base["Ganho_Potencial"] = 0

    base["Ganho_Potencial"] = pd.to_numeric(
        base["Ganho_Potencial"],
        errors="coerce"
    ).fillna(0)

    # Aliases seguros para telas ou exportações que precisem do ganho atualizado.
    base["Ganho_Potencial_Atualizado"] = base["Ganho_Potencial"]
    base["Ganho_Potencial_Final"] = base["Ganho_Potencial"]

    return base



def preparar_ganho_oficial_dashboard(base):
    """
    Usa exclusivamente o Ganho_Potencial da Analise_Pricing.xlsx.
    Não usa simulacao_global, histórico ou fallback.
    """

    base = base.copy()

    if "Ganho_Potencial" not in base.columns:
        base["Ganho_Potencial"] = 0

    base["Ganho_Potencial"] = pd.to_numeric(
        base["Ganho_Potencial"],
        errors="coerce"
    ).fillna(0)

    # Remove Total Geral, caso exista
    for coluna_nome in ["Produto", "Marca", "Laboratório", "Descricao_Unica"]:

        if coluna_nome in base.columns:

            base = base[
                ~base[coluna_nome]
                .astype(str)
                .str.upper()
                .str.strip()
                .eq("TOTAL GERAL")
            ].copy()

    # Remove ganhos absurdos provocados por leitura/fallback indevido
    base = base[
        base["Ganho_Potencial"].between(
            0,
            10_000_000
        )
    ].copy()

    return base



from pricing_utils import (
carregar_historico,
carregar_compra,
carregar_venda_rede,
carregar_estoque,
identificar_rede,
curva_abc
)


# --------------------------------------------------
# PADRONIZAÇÃO DO NOME DA REDE
# --------------------------------------------------

def limpar_nome_rede_eirox(valor_rede="", valor_loja=""):
    """
    Retorna somente o nome comercial da rede.
    Usa a coluna Rede quando existir; se estiver vazia, identifica pela loja/razão social.
    """

    def _texto_valido(valor):
        texto = str(valor).strip() if valor is not None else ""
        if texto.lower() in ["", "nan", "none", "nat"]:
            return ""
        return texto

    rede = _texto_valido(valor_rede)
    loja = _texto_valido(valor_loja)
    texto_base = rede if rede else loja

    if not texto_base:
        return ""

    texto_upper = texto_base.upper()

    # Mapeamentos principais encontrados nas pesquisas de mercado.
    mapa = [
        ("TRIANGULO", "Triângulo"),
        ("TRIÂNGULO", "Triângulo"),
        ("RAIADROGASIL", "Drogasil"),
        ("DROGASIL", "Drogasil"),
        ("DROGA RAIA", "Droga Raia"),
        (" ZANOL", "Zanol e Thomaz"),
        ("ZANOL", "Zanol e Thomaz"),
        ("BRASIFARMA", "Brasifarma"),
        ("PAGUE MENOS", "Pague Menos"),
        ("MARCOPHARMA", "Marcopharma"),
        ("BARBOSA", "Barbosa"),
        ("ADRI", "Adriele"),
        ("IR BRANDAO", "IR Brandão"),
        ("IR BRANDÃO", "IR Brandão"),
        ("PG COMERCIO", "PG Varejista"),
        ("PG COMÉRCIO", "PG Varejista"),
        ("PG - VAREJISTA", "PG Varejista"),
        ("MATEUS", "Mateus"),
    ]

    for termo, nome in mapa:
        if termo in texto_upper:
            return nome

    # Tenta usar a função padrão do projeto, caso reconheça a rede.
    try:
        rede_identificada = identificar_rede(texto_base)
        rede_identificada = _texto_valido(rede_identificada)
        if rede_identificada and rede_identificada.upper() not in ["OUTRAS", "OUTROS", "NÃO IDENTIFICADO", "NAO IDENTIFICADO"]:
            return rede_identificada
    except Exception:
        pass

    # Se veio no padrão "Rede - Razão Social", mantém só a rede.
    if " - " in texto_base:
        partes = [p.strip() for p in texto_base.split(" - ") if p.strip()]
        if len(partes) >= 2 and partes[0].upper() == "PG":
            return "PG Varejista"
        if partes:
            return partes[0]

    # Último fallback: remove termos jurídicos mais comuns.
    texto = re.sub(r"\b(COMERCIO|COMÉRCIO|DE|DO|DA|DOS|DAS|MEDICAMENTOS|PRODUTOS|FARMACEUTICOS|FARMACÊUTICOS|LTDA|S\.?A\.?|SA|EIRELI|ME|S/A)\b", "", texto_base, flags=re.IGNORECASE)
    texto = re.sub(r"\s+", " ", texto).strip(" -")
    return texto.title() if texto else texto_base


def serie_nome_rede_eirox(df_temp, coluna_rede=None, coluna_loja=None):
    """Cria uma Série com o nome limpo da rede a partir de Rede e/ou Loja."""
    if not isinstance(df_temp, pd.DataFrame) or df_temp.empty:
        return pd.Series(dtype="object")

    if coluna_rede and coluna_rede in df_temp.columns:
        serie_rede = df_temp[coluna_rede]
    else:
        serie_rede = pd.Series([""] * len(df_temp), index=df_temp.index)

    if coluna_loja and coluna_loja in df_temp.columns:
        serie_loja = df_temp[coluna_loja]
    else:
        serie_loja = pd.Series([""] * len(df_temp), index=df_temp.index)

    return pd.Series(
        [limpar_nome_rede_eirox(r, l) for r, l in zip(serie_rede, serie_loja)],
        index=df_temp.index
    )




# --------------------------------------------------
# BUSCA RECURSIVA DE BASES POR COLUNAS
# --------------------------------------------------

def carregar_base_recursiva_por_colunas(
    nome_base,
    colunas_obrigatorias,
    ignorar_pastas=None
):

    """
    Procura arquivos .xls, .xlsx, .xlsm e .csv em todo o projeto,
    identifica a base pelas colunas obrigatórias e concatena os arquivos encontrados.

    Útil para Streamlit Cloud quando a pasta foi criada fora do local esperado
    ou quando o GitHub mudou a estrutura de diretórios.
    """

    ignorar_pastas = ignorar_pastas or [
        ".git",
        ".streamlit",
        "__pycache__",
        ".venv",
        "venv"
    ]

    arquivos = []

    for ext in [
        "*.xls",
        "*.xlsx",
        "*.xlsm",
        "*.csv"
    ]:

        arquivos.extend(
            list(
                Path(".").rglob(ext)
            )
        )

    bases = []
    erros = []

    obrigatorias_norm = [
        str(c).strip().lower()
        for c in colunas_obrigatorias
    ]

    for arquivo in sorted(arquivos):

        partes = [
            p.lower()
            for p in arquivo.parts
        ]

        if any(p in partes for p in ignorar_pastas):
            continue

        # Evita reler a planilha principal como venda final.
        if arquivo.name.lower() == "analise_pricing.xlsx":
            continue

        try:

            if arquivo.suffix.lower() == ".csv":

                try:
                    temp = pd.read_csv(
                        arquivo,
                        sep=";",
                        encoding="utf-8-sig"
                    )
                except Exception:
                    temp = pd.read_csv(
                        arquivo,
                        encoding="utf-8-sig"
                    )

            else:

                temp = pd.read_excel(
                    arquivo
                )

            if temp.empty:
                continue

            temp.columns = (
                temp.columns
                .astype(str)
                .str.strip()
            )

            colunas_norm = [
                str(c).strip().lower()
                for c in temp.columns
            ]

            encontrou = all(
                col in colunas_norm
                for col in obrigatorias_norm
            )

            if encontrou:

                temp["Arquivo_Origem"] = arquivo.name
                temp["Fonte_Carregamento"] = str(arquivo.parent)
                bases.append(temp)

        except Exception as erro:

            erros.append(
                {
                    "Arquivo": str(arquivo),
                    "Erro": str(erro)
                }
            )

    if bases:

        base = pd.concat(
            bases,
            ignore_index=True
        )

        base.columns = (
            base.columns
            .astype(str)
            .str.strip()
        )

        return base

    # Guarda erros para diagnóstico se necessário
    globals()[f"ERROS_CARGA_{nome_base}"] = erros

    return pd.DataFrame()


# --------------------------------------------------
# LEITURA COMPATÍVEL DE EXCEL / CSV
# --------------------------------------------------

def carregar_pasta_excel_compat(pastas, nome_base="base"):

    bases = []

    for pasta_nome in pastas:

        pasta = Path(pasta_nome)

        if not pasta.exists() or not pasta.is_dir():
            continue

        arquivos = []

        for ext in [
            "*.xls",
            "*.xlsx",
            "*.xlsm",
            "*.csv"
        ]:
            arquivos.extend(list(pasta.glob(ext)))

        for arquivo in sorted(arquivos):

            try:

                if arquivo.suffix.lower() == ".csv":

                    try:
                        temp = pd.read_csv(
                            arquivo,
                            sep=";",
                            encoding="utf-8-sig"
                        )
                    except Exception:
                        temp = pd.read_csv(
                            arquivo,
                            encoding="utf-8-sig"
                        )

                else:

                    temp = pd.read_excel(
                        arquivo
                    )

                if not temp.empty:

                    temp["Arquivo_Origem"] = arquivo.name
                    temp["Fonte_Carregamento"] = str(pasta)
                    bases.append(temp)

            except Exception as erro:

                print(
                    f"Falha ao ler {nome_base} / {arquivo}: {erro}"
                )

    if bases:

        base = pd.concat(
            bases,
            ignore_index=True
        )

        base.columns = (
            base.columns
            .astype(str)
            .str.strip()
        )

        return base

    return pd.DataFrame()


# --------------------------------------------------
# MOTOR INTELIGENTE DE GANHO POTENCIAL
# --------------------------------------------------

def ler_base_pasta_ou_zip(pastas, zips):

    bases = []

    for pasta_nome in pastas:

        pasta = Path(pasta_nome)

        if pasta.exists() and pasta.is_dir():

            arquivos = []

            for ext in ["*.xlsx", "*.xls", "*.csv"]:
                arquivos.extend(list(pasta.glob(ext)))

            for arq in arquivos:

                try:

                    if arq.suffix.lower() == ".csv":

                        try:
                            temp = pd.read_csv(arq, sep=";", encoding="utf-8-sig")
                        except Exception:
                            temp = pd.read_csv(arq, encoding="utf-8-sig")

                    else:

                        temp = pd.read_excel(arq)

                    if not temp.empty:
                        temp["Arquivo_Origem"] = arq.name
                        bases.append(temp)

                except Exception as erro:
                    print(f"Falha ao ler {arq}: {erro}")

    if not bases:

        for zip_nome in zips:

            zip_path = Path(zip_nome)

            if not zip_path.exists():
                continue

            try:

                with zipfile.ZipFile(zip_path, "r") as z:

                    for nome in z.namelist():

                        if not nome.lower().endswith((".xlsx", ".xls", ".csv")):
                            continue

                        try:

                            with z.open(nome) as f:

                                if nome.lower().endswith(".csv"):

                                    try:
                                        temp = pd.read_csv(f, sep=";", encoding="utf-8-sig")
                                    except Exception:
                                        f.seek(0)
                                        temp = pd.read_csv(f, encoding="utf-8-sig")

                                else:

                                    temp = pd.read_excel(f)

                            if not temp.empty:
                                temp["Arquivo_Origem"] = nome
                                bases.append(temp)

                        except Exception as erro:
                            print(f"Falha ao ler {nome}: {erro}")

            except Exception as erro:
                print(f"Falha ao abrir zip {zip_nome}: {erro}")

    if bases:

        base = pd.concat(bases, ignore_index=True)
        base.columns = base.columns.astype(str).str.strip()
        return base

    return pd.DataFrame()


def achar_coluna(base, exatos, contem):

    if not isinstance(base, pd.DataFrame) or base.empty:
        return None

    for alvo in exatos:

        for col in base.columns:

            if str(col).strip().lower() == str(alvo).strip().lower():
                return col

    for termo in contem:

        termo = str(termo).lower()

        for col in base.columns:

            if termo in str(col).lower():
                return col

    return None


def converter_numero_brasil(serie):
    """
    Converte números em formatos brasileiros e americanos.
    Ex.: '1.234,56', '1234,56', '1,234.56', '1234.56'
    """

    if isinstance(serie, pd.Series):

        s = (
            serie
            .astype(str)
            .str.strip()
            .str.replace("R$", "", regex=False)
            .str.replace("%", "", regex=False)
            .str.replace(" ", "", regex=False)
        )

        # Se tiver vírgula, assume vírgula como decimal e ponto como milhar.
        tem_virgula = s.str.contains(",", regex=False)

        s_br = (
            s[tem_virgula]
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )

        s_us = (
            s[~tem_virgula]
            .str.replace(",", "", regex=False)
        )

        out = pd.Series(index=serie.index, dtype="float64")
        out.loc[s_br.index] = pd.to_numeric(s_br, errors="coerce")
        out.loc[s_us.index] = pd.to_numeric(s_us, errors="coerce")

        return out

    return pd.to_numeric(serie, errors="coerce")



def preco_referencia_seguro(valores):

    s = pd.to_numeric(valores, errors="coerce").dropna()
    s = s[(s > 0) & (s <= 5000)]

    if s.empty:
        return np.nan

    if len(s) >= 4:

        q1 = s.quantile(0.25)
        q3 = s.quantile(0.75)
        iqr = q3 - q1

        s2 = s[
            (s >= max(q1 - 1.5 * iqr, 0))
            & (s <= q3 + 1.5 * iqr)
        ]

        if not s2.empty:
            s = s2

    # Percentil 75 gera oportunidade sem usar preço extremo.
    return float(s.quantile(0.75))


def recalcular_ganho_inteligente(df_base, venda_rede_base, historico_base):

    if (
        not isinstance(df_base, pd.DataFrame)
        or df_base.empty
        or not isinstance(venda_rede_base, pd.DataFrame)
        or venda_rede_base.empty
        or not isinstance(historico_base, pd.DataFrame)
        or historico_base.empty
    ):
        return df_base.copy(), pd.DataFrame(), "sem_base_completa"

    df_calc = df_base.copy()
    venda = venda_rede_base.copy()
    hist = historico_base.copy()

    df_calc.columns = df_calc.columns.astype(str).str.strip()
    venda.columns = venda.columns.astype(str).str.strip()
    hist.columns = hist.columns.astype(str).str.strip()

    col_ean_venda = achar_coluna(
        venda,
        ["EAN", "EAN (GTIN)", "GTIN", "Código de Barras", "Codigo de Barras", "Cód. Barras/Etiq."],
        ["ean", "gtin", "barras"]
    )

    col_qtd = achar_coluna(
        venda,
        [
            "Itens",
            "Item",
            "Quantidade",
            "Qtd",
            "QTD",
            "Qtde",
            "Quantidade Vendida",
            "Qtd Vendida",
            "Unidades"
        ],
        [
            "itens",
            "item",
            "qtd",
            "quant",
            "qtde",
            "unid"
        ]
    )

    col_preco_venda = achar_coluna(
        venda,
        [
            "Preço Venda",
            "Preco Venda",
            "Preço (R$)",
            "Preco (R$)",
            "Valor Unitário",
            "Valor Unitario",
            "Preço Médio",
            "Preco Medio",
            "Preco_Medio"
        ],
        [
            "preço",
            "preco",
            "unit",
            "medio",
            "médio"
        ]
    )

    col_valor_total = achar_coluna(
        venda,
        [
            "Venda",
            "Valor Venda",
            "Faturamento",
            "Valor Líquido",
            "Valor Liquido",
            "Total Venda",
            "Valor Total"
        ],
        [
            "venda",
            "fatur",
            "liquido",
            "líquido"
        ]
    )

    col_prod_venda = achar_coluna(
        venda,
        ["Produto", "Descrição", "Descricao", "Nome Produto", "Embalagem"],
        ["produto", "descr", "embalagem"]
    )

    col_ean_hist = achar_coluna(
        hist,
        ["EAN", "EAN (GTIN)", "GTIN", "Código de Barras", "Codigo de Barras"],
        ["ean", "gtin", "barras"]
    )

    col_preco_hist = achar_coluna(
        hist,
        ["Preço (R$)", "Preco (R$)", "Preço", "Preco", "Valor"],
        ["preço", "preco", "valor"]
    )

    col_rede_hist = achar_coluna(
        hist,
        ["Rede", "Rede Concorrente", "Bandeira", "Grupo", "Concorrente"],
        ["rede", "bandeira", "grupo", "concorr"]
    )

    col_loja_hist = achar_coluna(
        hist,
        ["Farmácia", "Farmacia", "Loja", "Estabelecimento", "Razão Social", "Razao Social"],
        ["farm", "loja", "estabelec", "razão", "razao", "social"]
    )

    col_data_hist = achar_coluna(
        hist,
        ["Data", "Data Pesquisa", "Data da Pesquisa", "Dt Pesquisa", "Data_Hora", "Data Hora"],
        ["data", "dt"]
    )

    # Em bases tipo VENDA_FINAL_TESTE, a coluna "Venda" é total e "Itens" é quantidade.
    # Quando existir Venda + Itens, usar essa combinação para preço atual.
    if col_valor_total and col_qtd:
        col_preco_venda = None

    if (
        not col_ean_venda
        or not col_qtd
        or not col_ean_hist
        or not col_preco_hist
        or not (col_preco_venda or col_valor_total)
        or "EAN" not in df_calc.columns
    ):
        return df_calc, pd.DataFrame(), "colunas_incompletas"

    venda["EAN"] = venda[col_ean_venda].astype(str).str.replace(".0", "", regex=False).str.strip()
    hist["EAN"] = hist[col_ean_hist].astype(str).str.replace(".0", "", regex=False).str.strip()
    df_calc["EAN"] = df_calc["EAN"].astype(str).str.replace(".0", "", regex=False).str.strip()

    venda[col_qtd] = converter_numero_brasil(venda[col_qtd])
    hist[col_preco_hist] = converter_numero_brasil(hist[col_preco_hist])

    hist = hist[(hist[col_preco_hist] > 0) & (hist[col_preco_hist] <= 5000)].copy()

    if col_preco_venda:

        venda[col_preco_venda] = converter_numero_brasil(venda[col_preco_venda])

        vendas = (
            venda
            .dropna(subset=["EAN", col_qtd, col_preco_venda])
            .groupby("EAN")
            .agg(
                Qtd_Vendida_Mes_Anterior=(col_qtd, "sum"),
                Preco_Atual=(col_preco_venda, "mean")
            )
            .reset_index()
        )

        vendas["Venda_Preco_Antigo"] = vendas["Qtd_Vendida_Mes_Anterior"] * vendas["Preco_Atual"]

    else:

        venda[col_valor_total] = converter_numero_brasil(venda[col_valor_total])

        vendas = (
            venda
            .dropna(subset=["EAN", col_qtd, col_valor_total])
            .groupby("EAN")
            .agg(
                Qtd_Vendida_Mes_Anterior=(col_qtd, "sum"),
                Venda_Preco_Antigo=(col_valor_total, "sum")
            )
            .reset_index()
        )

        vendas = vendas[vendas["Qtd_Vendida_Mes_Anterior"] > 0].copy()
        vendas["Preco_Atual"] = vendas["Venda_Preco_Antigo"] / vendas["Qtd_Vendida_Mes_Anterior"]

    mercado = (
        hist
        .dropna(subset=["EAN", col_preco_hist])
        .groupby("EAN")[col_preco_hist]
        .apply(preco_referencia_seguro)
        .reset_index()
        .rename(columns={col_preco_hist: "Preco_Sugerido_Mercado"})
    )

    # Identifica a rede/loja/data que mais se aproxima do preço máximo competitivo
    # e também a rede/loja/data do menor preço encontrado no mercado.
    hist_ref = hist.dropna(subset=["EAN", col_preco_hist]).copy()
    hist_ref["Preco_Historico_Ref"] = pd.to_numeric(hist_ref[col_preco_hist], errors="coerce")
    hist_ref = hist_ref[(hist_ref["Preco_Historico_Ref"] > 0) & (hist_ref["Preco_Historico_Ref"] <= 5000)].copy()

    if not hist_ref.empty and not mercado.empty:
        hist_ref = hist_ref.merge(mercado, on="EAN", how="left")
        hist_ref["Dif_Preco_Maximo"] = (hist_ref["Preco_Historico_Ref"] - hist_ref["Preco_Sugerido_Mercado"]).abs()

        idx_max = hist_ref.groupby("EAN")["Dif_Preco_Maximo"].idxmin()
        ref_max = hist_ref.loc[idx_max].copy()

        idx_min = hist_ref.groupby("EAN")["Preco_Historico_Ref"].idxmin()
        ref_min = hist_ref.loc[idx_min].copy()

        def _col_ou_vazio(df_temp, coluna):
            return df_temp[coluna].astype(str).str.strip() if coluna and coluna in df_temp.columns else ""

        meta_max = pd.DataFrame({
            "EAN": ref_max["EAN"].astype(str),
            "Rede_Preco_Maximo_Competitivo": serie_nome_rede_eirox(ref_max, col_rede_hist, col_loja_hist),
            "Loja_Preco_Maximo_Competitivo": _col_ou_vazio(ref_max, col_loja_hist),
            "Data_Preco_Maximo_Competitivo": ref_max[col_data_hist] if col_data_hist and col_data_hist in ref_max.columns else ""
        })

        meta_min = pd.DataFrame({
            "EAN": ref_min["EAN"].astype(str),
            "Menor_Preco": ref_min["Preco_Historico_Ref"],
            "Rede_Menor_Preco": serie_nome_rede_eirox(ref_min, col_rede_hist, col_loja_hist),
            "Loja_Menor_Preco": _col_ou_vazio(ref_min, col_loja_hist),
            "Data_Menor_Preco": ref_min[col_data_hist] if col_data_hist and col_data_hist in ref_min.columns else ""
        })

        mercado = (
            mercado
            .merge(meta_max, on="EAN", how="left")
            .merge(meta_min, on="EAN", how="left")
        )

    simulacao = vendas.merge(mercado, on="EAN", how="inner")

    simulacao["Preco_Atual"] = pd.to_numeric(simulacao["Preco_Atual"], errors="coerce")
    simulacao["Preco_Sugerido_Mercado"] = pd.to_numeric(simulacao["Preco_Sugerido_Mercado"], errors="coerce")

    simulacao = simulacao[
        (simulacao["Qtd_Vendida_Mes_Anterior"] > 0)
        & (simulacao["Preco_Atual"] > 0)
        & (simulacao["Preco_Sugerido_Mercado"] > 0)
        & (simulacao["Preco_Sugerido_Mercado"] <= simulacao["Preco_Atual"] * 3)
        & (simulacao["Preco_Sugerido_Mercado"] >= simulacao["Preco_Atual"] * 0.5)
    ].copy()

    simulacao["Venda_Projetada_Preco_Sugerido"] = simulacao["Qtd_Vendida_Mes_Anterior"] * simulacao["Preco_Sugerido_Mercado"]
    simulacao["Ganho_Unitario"] = simulacao["Preco_Sugerido_Mercado"] - simulacao["Preco_Atual"]
    simulacao["Ganho_Potencial_Simulador"] = simulacao["Venda_Projetada_Preco_Sugerido"] - simulacao["Venda_Preco_Antigo"]

    simulacao = simulacao[simulacao["Ganho_Potencial_Simulador"] > 0].copy()

    if col_prod_venda and not simulacao.empty:

        prod_ref = (
            venda
            .groupby("EAN")[col_prod_venda]
            .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else x.iloc[0])
            .reset_index()
            .rename(columns={col_prod_venda: "Produto_Simulador"})
        )

        simulacao = simulacao.merge(prod_ref, on="EAN", how="left")

    for c in [
        "Preco_Atual",
        "Preco_Sugerido_Mercado",
        "Menor_Preco",
        "Ganho_Unitario",
        "Venda_Preco_Antigo",
        "Venda_Projetada_Preco_Sugerido",
        "Ganho_Potencial_Simulador",
        "Qtd_Vendida_Mes_Anterior"
    ]:
        if c in simulacao.columns:
            simulacao[c] = pd.to_numeric(simulacao[c], errors="coerce").round(2)

    if "Ganho_Potencial" in df_calc.columns:
        df_calc["Ganho_Potencial_Oficial"] = pd.to_numeric(df_calc["Ganho_Potencial"], errors="coerce").fillna(0)
    else:
        df_calc["Ganho_Potencial_Oficial"] = 0

    if simulacao.empty:
        df_calc["Ganho_Potencial"] = df_calc["Ganho_Potencial_Oficial"]
        return df_calc, simulacao, "sem_oportunidade_valida"

    ganho = simulacao[["EAN", "Ganho_Potencial_Simulador"]].rename(
        columns={"Ganho_Potencial_Simulador": "Ganho_Potencial_Inteligente"}
    )

    df_calc = df_calc.merge(ganho, on="EAN", how="left")

    df_calc["Ganho_Potencial_Inteligente"] = pd.to_numeric(
        df_calc["Ganho_Potencial_Inteligente"],
        errors="coerce"
    ).fillna(0)

    # Regra premium: usa o maior ganho válido entre o oficial e o recalculado.
    df_calc["Ganho_Potencial"] = df_calc[
        ["Ganho_Potencial_Oficial", "Ganho_Potencial_Inteligente"]
    ].max(axis=1)

    return df_calc, simulacao, "venda_rede_historico_inteligente"



# --------------------------------------------------
# LEITURA ROBUSTA DE BASES PARA ONLINE / LOCALHOST
# --------------------------------------------------

def _ler_excel_csv_pasta(pasta):
    pasta = Path(pasta)
    if not pasta.exists() or not pasta.is_dir():
        return pd.DataFrame()

    arquivos = []
    for ext in ["*.xlsx", "*.xls", "*.csv"]:
        arquivos.extend(list(pasta.glob(ext)))

    bases = []
    for arq in arquivos:
        try:
            if arq.suffix.lower() == ".csv":
                try:
                    temp = pd.read_csv(arq, sep=";", encoding="utf-8-sig")
                except Exception:
                    temp = pd.read_csv(arq, encoding="utf-8-sig")
            else:
                temp = pd.read_excel(arq)

            if not temp.empty:
                temp["Arquivo_Origem"] = arq.name
                bases.append(temp)
        except Exception as erro:
            print(f"Falha ao ler {arq}: {erro}")

    if bases:
        base = pd.concat(bases, ignore_index=True)
        base.columns = base.columns.astype(str).str.strip()
        return base

    return pd.DataFrame()


def _ler_excel_csv_zip(zip_nome):
    zip_path = Path(zip_nome)
    if not zip_path.exists():
        return pd.DataFrame()

    bases = []
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            for nome in z.namelist():
                if not nome.lower().endswith((".xlsx", ".xls", ".csv")):
                    continue

                try:
                    with z.open(nome) as f:
                        if nome.lower().endswith(".csv"):
                            try:
                                temp = pd.read_csv(f, sep=";", encoding="utf-8-sig")
                            except Exception:
                                f.seek(0)
                                temp = pd.read_csv(f, encoding="utf-8-sig")
                        else:
                            temp = pd.read_excel(f)

                    if not temp.empty:
                        temp["Arquivo_Origem"] = nome
                        bases.append(temp)
                except Exception as erro:
                    print(f"Falha ao ler {nome} em {zip_nome}: {erro}")
    except Exception as erro:
        print(f"Falha ao abrir zip {zip_nome}: {erro}")

    if bases:
        base = pd.concat(bases, ignore_index=True)
        base.columns = base.columns.astype(str).str.strip()
        return base

    return pd.DataFrame()


def carregar_base_robusta(nome_base, pastas, zips):
    for pasta in pastas:
        base = _ler_excel_csv_pasta(pasta)
        if not base.empty:
            base["Fonte_Carregamento"] = pasta
            return base

    for zip_nome in zips:
        base = _ler_excel_csv_zip(zip_nome)
        if not base.empty:
            base["Fonte_Carregamento"] = zip_nome
            return base

    print(f"{nome_base} não encontrada.")
    return pd.DataFrame()


def encontrar_coluna_flexivel(base, opcoes, contem=None):
    if not isinstance(base, pd.DataFrame) or base.empty:
        return None

    colunas = base.columns.astype(str).tolist()

    for opcao in opcoes:
        for coluna in colunas:
            if coluna.strip().lower() == str(opcao).strip().lower():
                return coluna

    if contem:
        for coluna in colunas:
            nome = str(coluna).lower()
            if any(str(t).lower() in nome for t in contem):
                return coluna

    return None


def _preco_ref_seguro(s):
    s = pd.to_numeric(s, errors="coerce").dropna()
    s = s[(s > 0) & (s <= 5000)]

    if s.empty:
        return None

    if len(s) >= 4:
        q1 = s.quantile(0.25)
        q3 = s.quantile(0.75)
        iqr = q3 - q1
        lim_inf = max(q1 - 1.5 * iqr, 0)
        lim_sup = q3 + 1.5 * iqr
        s2 = s[(s >= lim_inf) & (s <= lim_sup)]
        if not s2.empty:
            s = s2

    return float(s.median())


def criar_simulacao_por_historico(historico_base):
    if not isinstance(historico_base, pd.DataFrame) or historico_base.empty:
        return pd.DataFrame()

    base = historico_base.copy()
    base.columns = base.columns.astype(str).str.strip()

    col_ean = encontrar_coluna_flexivel(
        base,
        ["EAN", "EAN (GTIN)", "GTIN", "Código de Barras", "Codigo de Barras"],
        ["ean", "gtin", "barras"]
    )

    col_produto = encontrar_coluna_flexivel(
        base,
        ["Produto", "Descrição", "Descricao", "Termo Pesquisado"],
        ["produto", "descr", "termo"]
    )

    col_preco = encontrar_coluna_flexivel(
        base,
        ["Preço (R$)", "Preco (R$)", "Preço", "Preco", "Valor"],
        ["preço", "preco", "valor"]
    )

    col_rede = encontrar_coluna_flexivel(
        base,
        ["Rede", "Rede Concorrente", "Bandeira", "Grupo", "Concorrente"],
        ["rede", "bandeira", "grupo", "concorr"]
    )

    col_loja = encontrar_coluna_flexivel(
        base,
        ["Farmácia", "Farmacia", "Loja", "Estabelecimento", "Razão Social", "Razao Social"],
        ["farm", "loja", "estabelec", "razão", "razao", "social"]
    )

    col_data = encontrar_coluna_flexivel(
        base,
        ["Data", "Data Pesquisa", "Data da Pesquisa", "Dt Pesquisa", "Data_Hora", "Data Hora"],
        ["data", "dt"]
    )

    if not col_ean or not col_preco:
        return pd.DataFrame()

    base["EAN"] = base[col_ean].astype(str).str.replace(".0", "", regex=False).str.strip()
    base["Preco_Base"] = pd.to_numeric(base[col_preco], errors="coerce")
    base = base.dropna(subset=["EAN", "Preco_Base"])
    base = base[(base["Preco_Base"] > 0) & (base["Preco_Base"] <= 5000)].copy()

    if base.empty:
        return pd.DataFrame()

    simulacao = (
        base
        .groupby("EAN")
        .agg(
            Qtd_Vendida_Mes_Anterior=("Preco_Base", "count"),
            Preco_Atual=("Preco_Base", "mean"),
            Preco_Sugerido_Mercado=("Preco_Base", _preco_ref_seguro)
        )
        .reset_index()
    )

    if col_produto:
        produto_ref = (
            base.groupby("EAN")[col_produto]
            .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else x.iloc[0])
            .reset_index()
            .rename(columns={col_produto: "Produto_Simulador"})
        )
        simulacao = simulacao.merge(produto_ref, on="EAN", how="left")

    simulacao["Preco_Atual"] = pd.to_numeric(simulacao["Preco_Atual"], errors="coerce")
    simulacao["Preco_Sugerido_Mercado"] = pd.to_numeric(simulacao["Preco_Sugerido_Mercado"], errors="coerce")

    simulacao = simulacao[
        (simulacao["Preco_Atual"] > 0)
        & (simulacao["Preco_Sugerido_Mercado"] > 0)
        & (simulacao["Preco_Sugerido_Mercado"] <= simulacao["Preco_Atual"] * 3)
    ].copy()

    # Complementa o simulador com rede/loja/data do preço máximo competitivo
    # e do menor preço encontrado no histórico de pesquisa.
    base_ref = base[[c for c in ["EAN", "Preco_Base", col_rede, col_loja, col_data] if c and c in base.columns]].copy()
    if not base_ref.empty and not simulacao.empty:
        base_ref = base_ref.merge(simulacao[["EAN", "Preco_Sugerido_Mercado"]], on="EAN", how="left")
        base_ref["Dif_Preco_Maximo"] = (base_ref["Preco_Base"] - base_ref["Preco_Sugerido_Mercado"]).abs()

        idx_max = base_ref.groupby("EAN")["Dif_Preco_Maximo"].idxmin()
        ref_max = base_ref.loc[idx_max].copy()

        idx_min = base_ref.groupby("EAN")["Preco_Base"].idxmin()
        ref_min = base_ref.loc[idx_min].copy()

        def _col_ou_vazio(df_temp, coluna):
            return df_temp[coluna].astype(str).str.strip() if coluna and coluna in df_temp.columns else ""

        meta = pd.DataFrame({
            "EAN": ref_max["EAN"].astype(str),
            "Rede_Preco_Maximo_Competitivo": serie_nome_rede_eirox(ref_max, col_rede, col_loja),
            "Loja_Preco_Maximo_Competitivo": _col_ou_vazio(ref_max, col_loja),
            "Data_Preco_Maximo_Competitivo": ref_max[col_data] if col_data and col_data in ref_max.columns else ""
        }).merge(
            pd.DataFrame({
                "EAN": ref_min["EAN"].astype(str),
                "Menor_Preco": ref_min["Preco_Base"],
                "Rede_Menor_Preco": serie_nome_rede_eirox(ref_min, col_rede, col_loja),
                "Loja_Menor_Preco": _col_ou_vazio(ref_min, col_loja),
                "Data_Menor_Preco": ref_min[col_data] if col_data and col_data in ref_min.columns else ""
            }),
            on="EAN",
            how="left"
        )

        simulacao = simulacao.merge(meta, on="EAN", how="left")

    simulacao["Venda_Preco_Antigo"] = simulacao["Qtd_Vendida_Mes_Anterior"] * simulacao["Preco_Atual"]
    simulacao["Venda_Projetada_Preco_Sugerido"] = simulacao["Qtd_Vendida_Mes_Anterior"] * simulacao["Preco_Sugerido_Mercado"]
    simulacao["Ganho_Unitario"] = simulacao["Preco_Sugerido_Mercado"] - simulacao["Preco_Atual"]
    simulacao["Ganho_Potencial_Simulador"] = simulacao["Venda_Projetada_Preco_Sugerido"] - simulacao["Venda_Preco_Antigo"]

    simulacao = simulacao[simulacao["Ganho_Potencial_Simulador"] > 0].copy()

    for c in [
        "Preco_Atual", "Preco_Sugerido_Mercado", "Menor_Preco", "Ganho_Unitario",
        "Venda_Preco_Antigo", "Venda_Projetada_Preco_Sugerido",
        "Ganho_Potencial_Simulador", "Qtd_Vendida_Mes_Anterior"
    ]:
        if c in simulacao.columns:
            simulacao[c] = simulacao[c].round(2)

    return simulacao


# --------------------------------------------------
# CONFIG
# --------------------------------------------------


st.set_page_config(
    page_title="Eirox Pricing Enterprise",
    layout="wide"
)

st.markdown(
    """
    <style>

/* ==================================================
   EIROX DARK ENTERPRISE PREMIUM
   Tema escuro corporativo para Streamlit
   ================================================== */

:root {
    --eirox-bg: #07111F;
    --eirox-panel: #0B1B33;
    --eirox-panel-2: #0F2747;
    --eirox-border: rgba(120, 180, 255, 0.18);
    --eirox-text: #F3F7FF;
    --eirox-muted: #AFC7E8;
    --eirox-blue: #2CA0FF;
    --eirox-blue-2: #0E64C8;
    --eirox-green: #2ED47A;
    --eirox-yellow: #FFB946;
    --eirox-red: #FF5C7A;
    --eirox-orange: #FF8A3D;
}

html, body, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at top left, rgba(44,160,255,0.15), transparent 32%),
        linear-gradient(135deg, #050B14 0%, #07111F 45%, #0A1C34 100%) !important;
    color: var(--eirox-text) !important;
}

[data-testid="stHeader"] {
    background: rgba(5, 11, 20, 0.72) !important;
    backdrop-filter: blur(14px);
    border-bottom: 1px solid rgba(120, 180, 255, 0.10);
}

.block-container {
    max-width: 100% !important;
    padding-top: 1.2rem !important;
    padding-left: 1.4rem !important;
    padding-right: 1.4rem !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background:
        radial-gradient(circle at top, rgba(44,160,255,0.28), transparent 30%),
        linear-gradient(180deg, #0E2A4F 0%, #071A33 58%, #04101F 100%) !important;
    border-right: 1px solid rgba(120, 180, 255, 0.18);
    box-shadow: 8px 0 28px rgba(0, 0, 0, 0.26);
}

section[data-testid="stSidebar"] .block-container {
    padding-top: 1.2rem !important;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span {
    color: #FFFFFF !important;
}

.sidebar-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.10), rgba(255,255,255,0.04));
    border: 1px solid rgba(180, 215, 255, 0.18);
    border-radius: 18px;
    padding: 16px 16px;
    margin-bottom: 14px;
    box-shadow: 0 14px 34px rgba(0, 0, 0, 0.22);
    backdrop-filter: blur(10px);
}

.sidebar-title {
    font-size: 19px;
    font-weight: 900;
    letter-spacing: .02em;
    color: #FFFFFF;
    margin-bottom: 4px;
}

.sidebar-subtitle {
    font-size: 12px;
    color: #C8DFFF;
}

.sidebar-section {
    font-size: 11px;
    font-weight: 900;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: #9FD0FF !important;
    margin-top: 18px;
    margin-bottom: 8px;
}

.sidebar-pill {
    display: inline-block;
    background: linear-gradient(135deg, rgba(44,160,255,.32), rgba(46,212,122,.16));
    border: 1px solid rgba(44,160,255,.48);
    color: #E6F4FF;
    padding: 5px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 800;
    margin-top: 6px;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label {
    background: rgba(255,255,255,0.065);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 13px;
    padding: 10px 10px;
    margin-bottom: 7px;
    transition: all .18s ease;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    background: rgba(44,160,255,0.18);
    border-color: rgba(44,160,255,0.42);
    transform: translateX(3px);
}

/* Títulos */
h1, h2, h3 {
    color: #F6FAFF !important;
    letter-spacing: -0.02em;
}

h1 {
    font-weight: 900 !important;
}

h4, p, span, label {
    color: var(--eirox-muted) !important;
}

/* Cards e containers */
div[data-testid="stMetric"] {
    background:
        linear-gradient(135deg, rgba(15,39,71,.98), rgba(8,20,38,.95));
    border: 1px solid rgba(120,180,255,.18);
    border-radius: 18px;
    padding: 18px 18px;
    box-shadow: 0 18px 42px rgba(0, 0, 0, 0.26);
    position: relative;
    overflow: hidden;
}

div[data-testid="stMetric"]::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 3px;
    background: linear-gradient(90deg, #2CA0FF, #2ED47A);
}

div[data-testid="stMetricLabel"] {
    color: #AFC7E8 !important;
    font-weight: 700;
}

div[data-testid="stMetricValue"] {
    color: #FFFFFF !important;
    font-weight: 900;
    font-size: 28px !important;
}

/* Alertas Streamlit */
div[data-testid="stAlert"] {
    background: linear-gradient(135deg, rgba(14,42,79,.88), rgba(7,26,51,.88)) !important;
    border: 1px solid rgba(120,180,255,.18) !important;
    border-radius: 16px !important;
    color: #EAF4FF !important;
    box-shadow: 0 12px 30px rgba(0, 0, 0, .18);
}

/* Inputs */
.stTextInput input,
.stSelectbox div[data-baseweb="select"] > div,
.stMultiSelect div[data-baseweb="select"] > div {
    background: rgba(6, 18, 34, 0.96) !important;
    color: #F6FAFF !important;
    border: 1px solid rgba(120,180,255,.22) !important;
    border-radius: 12px !important;
}

.stTextInput input:focus {
    border-color: rgba(44,160,255,.75) !important;
    box-shadow: 0 0 0 2px rgba(44,160,255,.18) !important;
}

/* Botões */
.stButton button,
.stDownloadButton button,
button[kind="primary"],
button[kind="secondary"] {
    background: linear-gradient(135deg, #0E64C8, #2CA0FF) !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(255,255,255,.18) !important;
    border-radius: 13px !important;
    font-weight: 800 !important;
    box-shadow: 0 10px 24px rgba(44,160,255,.25);
    transition: all .18s ease;
}

.stButton button:hover,
.stDownloadButton button:hover {
    transform: translateY(-1px);
    box-shadow: 0 14px 32px rgba(44,160,255,.34);
}

/* Dataframes */
div[data-testid="stDataFrame"] {
    width: 100% !important;
    border-radius: 18px !important;
    overflow: hidden !important;
    border: 1px solid rgba(120,180,255,.16);
    box-shadow: 0 16px 38px rgba(0, 0, 0, .24);
}

div[data-testid="stDataFrame"] > div {
    width: 100% !important;
    background: rgba(7, 17, 31, .88) !important;
}

/* Tabs e radios */
div[role="radiogroup"] label {
    color: #EAF4FF !important;
}

.stRadio label {
    color: #EAF4FF !important;
}

/* Plotly */
.js-plotly-plot,
.plotly,
.plot-container {
    border-radius: 18px !important;
}

/* Cards customizados opcionais */
.eirox-card {
    background: linear-gradient(135deg, rgba(15,39,71,.96), rgba(8,20,38,.94));
    border: 1px solid rgba(120,180,255,.17);
    border-radius: 18px;
    padding: 18px;
    box-shadow: 0 18px 42px rgba(0, 0, 0, .26);
    margin-bottom: 16px;
}

.eirox-section-title {
    font-size: 13px;
    color: #9FD0FF;
    text-transform: uppercase;
    letter-spacing: .12em;
    font-weight: 900;
    margin-bottom: 8px;
}

.eirox-hero {
    background:
        radial-gradient(circle at top right, rgba(44,160,255,.22), transparent 28%),
        linear-gradient(135deg, rgba(15,39,71,.96), rgba(7,17,31,.96));
    border: 1px solid rgba(120,180,255,.18);
    border-radius: 22px;
    padding: 22px 24px;
    margin-bottom: 18px;
    box-shadow: 0 18px 45px rgba(0,0,0,.30);
}

.eirox-hero h1 {
    margin: 0;
    font-size: 30px;
}

.eirox-hero p {
    margin: 6px 0 0 0;
    color: #BFD7FF !important;
}

/* Destaques por prioridade em HTML */
.tag-critical {
    background: rgba(255,92,122,.14);
    color: #FFD6DE;
    border: 1px solid rgba(255,92,122,.36);
    border-radius: 999px;
    padding: 3px 9px;
    font-weight: 800;
}

.tag-high {
    background: rgba(255,138,61,.14);
    color: #FFE3CF;
    border: 1px solid rgba(255,138,61,.36);
    border-radius: 999px;
    padding: 3px 9px;
    font-weight: 800;
}

.tag-medium {
    background: rgba(255,185,70,.14);
    color: #FFF1CF;
    border: 1px solid rgba(255,185,70,.36);
    border-radius: 999px;
    padding: 3px 9px;
    font-weight: 800;
}

.tag-low {
    background: rgba(46,212,122,.14);
    color: #D7FFE8;
    border: 1px solid rgba(46,212,122,.36);
    border-radius: 999px;
    padding: 3px 9px;
    font-weight: 800;
}

    </style>
    """,
    unsafe_allow_html=True
)


# --------------------------------------------------
# ALERTA TELEGRAM DE ACESSO
# --------------------------------------------------

def obter_config_telegram(nome):

    """
    Busca configuração primeiro no Streamlit Secrets e depois em variável de ambiente.
    Não deixa token sensível fixo no código.
    """

    try:
        if hasattr(st, "secrets") and nome in st.secrets:
            return str(st.secrets[nome]).strip()
    except Exception:
        pass

    try:
        return str(os.environ.get(nome, "")).strip()
    except Exception:
        return ""


def enviar_alerta_telegram(mensagem):

    """
    Envia alerta de acesso para Telegram.
    Para ativar no Streamlit Cloud, configurar em Secrets:

    TELEGRAM_BOT_TOKEN = "seu_token"
    TELEGRAM_CHAT_ID = "seu_chat_id"
    """

    token = obter_config_telegram("TELEGRAM_BOT_TOKEN")
    chat_id = obter_config_telegram("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        return False

    try:

        url = f"https://api.telegram.org/bot{token}/sendMessage"

        payload = urllib.parse.urlencode(
            {
                "chat_id": chat_id,
                "text": mensagem,
                "parse_mode": "HTML",
                "disable_web_page_preview": "true"
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=5) as resposta:
            return resposta.status == 200

    except Exception:
        return False



def horario_brasil_formatado():
    """
    Retorna horário do Brasil para alertas, corrigindo UTC do Streamlit Cloud.
    """

    try:
        return datetime.now(
            ZoneInfo("America/Sao_Paulo")
        ).strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return horario_brasil_formatado()



def obter_localizacao_query_params():
    try:
        params = st.query_params

        lat = params.get("geo_lat", "")
        lon = params.get("geo_lon", "")
        acc = params.get("geo_acc", "")
        status = params.get("geo_status", "")

        if isinstance(lat, list):
            lat = lat[0] if lat else ""
        if isinstance(lon, list):
            lon = lon[0] if lon else ""
        if isinstance(acc, list):
            acc = acc[0] if acc else ""
        if isinstance(status, list):
            status = status[0] if status else ""

        lat = str(lat).strip()
        lon = str(lon).strip()
        acc = str(acc).strip()
        status = str(status).strip()

        if lat and lon:
            st.session_state["geo_lat"] = lat
            st.session_state["geo_lon"] = lon
            st.session_state["geo_acc"] = acc
            st.session_state["geo_status"] = "autorizada"
        elif status:
            st.session_state["geo_status"] = status

        return {
            "lat": st.session_state.get("geo_lat", ""),
            "lon": st.session_state.get("geo_lon", ""),
            "acc": st.session_state.get("geo_acc", ""),
            "status": st.session_state.get("geo_status", "pendente")
        }

    except Exception:
        return {"lat": "", "lon": "", "acc": "", "status": "indisponivel"}


def texto_localizacao_telegram():
    try:
        geo = obter_localizacao_query_params()
        lat = geo.get("lat", "")
        lon = geo.get("lon", "")
        acc = geo.get("acc", "")
        status = geo.get("status", "pendente")

        if lat and lon:
            mapa = f"https://www.google.com/maps?q={lat},{lon}"
            if acc:
                return f"📍 <b>Localização:</b> {lat}, {lon}\n🎯 <b>Precisão:</b> {acc} metros\n🗺️ <b>Mapa:</b> {mapa}\n"
            return f"📍 <b>Localização:</b> {lat}, {lon}\n🗺️ <b>Mapa:</b> {mapa}\n"

        if status == "negada":
            return "📍 <b>Localização:</b> permissão negada pelo usuário\n"

        return "📍 <b>Localização:</b> aguardando permissão do navegador\n"

    except Exception:
        return "📍 <b>Localização:</b> indisponível\n"


def solicitar_localizacao_navegador():
    try:
        components.html(
            """
            <script>
            (function() {
                const params = new URLSearchParams(window.parent.location.search);

                if (params.get("geo_lat") && params.get("geo_lon")) {
                    return;
                }

                if (!navigator.geolocation) {
                    params.set("geo_status", "indisponivel");
                    window.parent.history.replaceState(null, "", "?" + params.toString());
                    return;
                }

                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        params.set("geo_lat", position.coords.latitude.toFixed(6));
                        params.set("geo_lon", position.coords.longitude.toFixed(6));
                        params.set("geo_acc", Math.round(position.coords.accuracy));
                        params.set("geo_status", "autorizada");
                        window.parent.history.replaceState(null, "", "?" + params.toString());
                    },
                    function(error) {
                        params.set("geo_status", "negada");
                        window.parent.history.replaceState(null, "", "?" + params.toString());
                    },
                    { enableHighAccuracy: true, timeout: 7000, maximumAge: 300000 }
                );
            })();
            </script>
            """,
            height=0,
            width=0
        )

        obter_localizacao_query_params()

    except Exception:
        pass


def enviar_alerta_localizacao_capturada():
    try:
        if not st.session_state.get("logado", False):
            return

        geo = obter_localizacao_query_params()

        if not geo.get("lat") or not geo.get("lon"):
            return

        if st.session_state.get("alerta_localizacao_enviado", False):
            return

        usuario = st.session_state.get("usuario", "")
        nome = st.session_state.get("nome_usuario", "")
        perfil = st.session_state.get("perfil_usuario", "")
        ambiente = "Streamlit Cloud" if "/mount/src" in str(Path.cwd()) else "Localhost"

        mensagem = (
            "📍 <b>Localização capturada no Eirox Pricing</b>\n\n"
            f"👤 <b>Usuário:</b> {usuario}\n"
            f"🙋 <b>Nome:</b> {nome}\n"
            f"🔐 <b>Perfil:</b> {perfil}\n"
            f"🕒 <b>Horário:</b> {horario_brasil_formatado()}\n"
            f"{texto_localizacao_telegram()}"
            f"🌐 <b>Ambiente:</b> {ambiente}\n"
            f"🏷️ <b>Versão:</b> {VERSAO_APP}"
        )

        if enviar_alerta_telegram(mensagem):
            st.session_state["alerta_localizacao_enviado"] = True

    except Exception:
        pass


def registrar_alerta_login(usuario, nome, perfil):

    """
    Envia alerta uma única vez por sessão autenticada.
    Evita disparos repetidos a cada rerun do Streamlit.
    """

    try:

        chave_sessao = f"alerta_login_enviado_{usuario}"

        if st.session_state.get(chave_sessao, False):
            return

        ambiente = "Streamlit Cloud" if "/mount/src" in str(Path.cwd()) else "Localhost"

        mensagem = (
            "🚀 <b>Novo acesso no Eirox Pricing</b>\n\n"
            f"👤 <b>Usuário:</b> {usuario}\n"
            f"🙋 <b>Nome:</b> {nome}\n"
            f"🔐 <b>Perfil:</b> {perfil}\n"
            f"🕒 <b>Horário:</b> {horario_brasil_formatado()}\n"
            f"{texto_localizacao_telegram()}"
            f"🌐 <b>Ambiente:</b> {ambiente}\n"
            f"🏷️ <b>Versão:</b> {VERSAO_APP}"
        )

        enviado = enviar_alerta_telegram(mensagem)

        if enviado:
            st.session_state[chave_sessao] = True

    except Exception:
        pass




# --------------------------------------------------
# CENTRAL DE AUDITORIA / LOGS DE ACESSO
# --------------------------------------------------

LOG_DIR = Path("logs")
LOG_ARQUIVO = LOG_DIR / "log_acessos.csv"


def usuario_pode_ver_auditoria():
    try:
        return usuario_master()
    except Exception:
        return False


def salvar_log_acesso(evento, tela="", detalhe=""):
    try:
        LOG_DIR.mkdir(exist_ok=True)

        ambiente = "Streamlit Cloud" if "/mount/src" in str(Path.cwd()) else "Localhost"

        linha = {
            "Data_Hora": horario_brasil_formatado() if "horario_brasil_formatado" in globals() else datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "Usuario": st.session_state.get("usuario", ""),
            "Nome": st.session_state.get("nome_usuario", ""),
            "Perfil": st.session_state.get("perfil_usuario", ""),
            "Evento": str(evento),
            "Tela": str(tela),
            "Detalhe": str(detalhe),
            "Latitude": st.session_state.get("geo_lat", ""),
            "Longitude": st.session_state.get("geo_lon", ""),
            "Precisao_Metros": st.session_state.get("geo_acc", ""),
            "Status_Localizacao": st.session_state.get("geo_status", ""),
            "Ambiente": ambiente,
            "Versao": VERSAO_APP
        }

        existe = LOG_ARQUIVO.exists()

        with open(LOG_ARQUIVO, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(linha.keys()), delimiter=";")
            if not existe:
                writer.writeheader()
            writer.writerow(linha)

    except Exception:
        pass


def carregar_logs_acesso():
    try:
        if not LOG_ARQUIVO.exists():
            return pd.DataFrame()

        logs = pd.read_csv(LOG_ARQUIVO, sep=";", encoding="utf-8-sig")

        if not logs.empty and "Data_Hora" in logs.columns:
            logs["Data_Hora_dt"] = pd.to_datetime(
                logs["Data_Hora"],
                format="%d/%m/%Y %H:%M:%S",
                errors="coerce"
            )

        return logs
    except Exception:
        return pd.DataFrame()



def exportar_auditoria_excel(logs_detalhe, ranking_usuarios, ranking_telas, acessos_dia):
    """
    Gera arquivo Excel da Central de Auditoria Avançada.
    """

    try:
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            logs_detalhe.to_excel(writer, index=False, sheet_name="Historico")
            ranking_usuarios.to_excel(writer, index=False, sheet_name="Ranking_Usuarios")
            ranking_telas.to_excel(writer, index=False, sheet_name="Ranking_Telas")
            acessos_dia.to_excel(writer, index=False, sheet_name="Acessos_por_Dia")

        output.seek(0)

        return output.getvalue()

    except Exception:
        return b""






# --------------------------------------------------
# BACKUP CENTER - HOMOLOGAÇÃO v1.35.4
# --------------------------------------------------

BACKUP_DIR = Path("backups_eirox")


def _backup_agora_tag():
    try:
        return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y%m%d_%H%M%S")
    except Exception:
        return datetime.now().strftime("%Y%m%d_%H%M%S")


def _backup_agora_br():
    try:
        return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def _backup_tamanho_formatado(bytes_valor):
    try:
        bytes_valor = float(bytes_valor)

        if bytes_valor >= 1024 ** 3:
            return f"{bytes_valor / (1024 ** 3):.2f} GB".replace(".", ",")

        if bytes_valor >= 1024 ** 2:
            return f"{bytes_valor / (1024 ** 2):.2f} MB".replace(".", ",")

        if bytes_valor >= 1024:
            return f"{bytes_valor / 1024:.2f} KB".replace(".", ",")

        return f"{int(bytes_valor)} B"

    except Exception:
        return "0 B"


def _backup_arquivos_alvo():
    return [
        "dashboard_pricing.py",
        "pricing_utils.py",
        "style.css",
        "logo eirox.png",
        "Analise_Pricing.xlsx",
        "VENDA_TESTE",
        "VENDA_FINAL_TESTE",
        "COMPRA_TESTE",
        "ESTOQUE_TESTE",
        "logs",
        "USUARIOS_EIROX.csv",
        ".streamlit"
    ]


def _backup_status_alvos():
    linhas = []

    for alvo in _backup_arquivos_alvo():
        p = Path(alvo)
        existe = p.exists()
        tipo = "Pasta" if existe and p.is_dir() else "Arquivo"
        tamanho = 0
        qtd_arquivos = 0
        atualizado_ts = None

        try:
            if existe and p.is_file():
                tamanho = p.stat().st_size
                qtd_arquivos = 1
                atualizado_ts = p.stat().st_mtime

            elif existe and p.is_dir():
                for arq in p.rglob("*"):
                    if arq.is_file():
                        qtd_arquivos += 1
                        tamanho += arq.stat().st_size
                        if atualizado_ts is None or arq.stat().st_mtime > atualizado_ts:
                            atualizado_ts = arq.stat().st_mtime

        except Exception:
            pass

        atualizado = ""
        try:
            if atualizado_ts:
                atualizado = datetime.fromtimestamp(atualizado_ts).strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            atualizado = ""

        linhas.append(
            {
                "Item": alvo,
                "Status": "🟢 Encontrado" if existe else "🟡 Não encontrado",
                "Tipo": tipo if existe else "-",
                "Arquivos": qtd_arquivos,
                "Tamanho": _backup_tamanho_formatado(tamanho),
                "Última Atualização": atualizado
            }
        )

    return pd.DataFrame(linhas)


def gerar_backup_eirox(nome_manual=""):
    try:
        BACKUP_DIR.mkdir(exist_ok=True)

        tag = _backup_agora_tag()
        nome_base = str(nome_manual).strip()

        if not nome_base:
            nome_base = f"BACKUP_EIROX_PRICING_{VERSAO_APP}_{tag}"

        nome_base = (
            nome_base
            .replace("/", "_")
            .replace("\\", "_")
            .replace(":", "_")
            .replace(" ", "_")
        )

        zip_path = BACKUP_DIR / f"{nome_base}.zip"

        itens_incluidos = []
        itens_ignorados = []

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:

            readme = (
                "EIROX PRICING ENTERPRISE - BACKUP OFICIAL\\n\\n"
                f"Versão: {VERSAO_APP}\\n"
                f"Data/Hora: {_backup_agora_br()}\\n"
                f"Gerado por: {st.session_state.get('usuario', '')}\\n\\n"
                "Conteúdo:\\n"
                "- Código principal\\n"
                "- Bases operacionais\\n"
                "- Logs\\n"
                "- Usuários\\n"
                "- Configurações locais disponíveis\\n\\n"
                "Observação: secrets do Streamlit Cloud não são exportados automaticamente por segurança.\\n"
            )

            z.writestr("README_BACKUP.txt", readme)

            for alvo in _backup_arquivos_alvo():
                p = Path(alvo)

                if not p.exists():
                    itens_ignorados.append(alvo)
                    continue

                if p.is_file():
                    z.write(p, arcname=str(p))
                    itens_incluidos.append(str(p))

                elif p.is_dir():
                    for arq in p.rglob("*"):
                        if not arq.is_file():
                            continue

                        if ".git" in arq.parts or "__pycache__" in arq.parts:
                            continue

                        # Evita backup dentro de backup gigante
                        if BACKUP_DIR.name in arq.parts:
                            continue

                        z.write(arq, arcname=str(arq))
                        itens_incluidos.append(str(arq))

        tamanho = zip_path.stat().st_size if zip_path.exists() else 0

        try:
            registrar_log_usuario(
                "Backup",
                str(zip_path.name),
                f"Backup gerado com {len(itens_incluidos)} itens. Ignorados: {len(itens_ignorados)}"
            )
        except Exception:
            pass

        try:
            enviar_alerta_telegram(
                "📦 <b>Backup gerado no Eirox Pricing</b>\\n\\n"
                f"📄 <b>Arquivo:</b> {zip_path.name}\\n"
                f"📦 <b>Tamanho:</b> {_backup_tamanho_formatado(tamanho)}\\n"
                f"✅ <b>Itens incluídos:</b> {len(itens_incluidos)}\\n"
                f"⚠️ <b>Itens não encontrados:</b> {len(itens_ignorados)}\\n"
                f"🕒 <b>Horário:</b> {_backup_agora_br()}\\n"
                f"👤 <b>Usuário:</b> {st.session_state.get('usuario', '')}\\n"
                f"🏷️ <b>Versão:</b> {VERSAO_APP}"
            )
        except Exception:
            pass

        return {
            "ok": True,
            "arquivo": str(zip_path),
            "nome": zip_path.name,
            "tamanho": tamanho,
            "itens_incluidos": len(itens_incluidos),
            "itens_ignorados": itens_ignorados
        }

    except Exception as erro:
        return {
            "ok": False,
            "erro": str(erro),
            "arquivo": "",
            "nome": "",
            "tamanho": 0,
            "itens_incluidos": 0,
            "itens_ignorados": []
        }


def listar_backups_eirox():
    try:
        BACKUP_DIR.mkdir(exist_ok=True)

        linhas = []

        for arq in sorted(BACKUP_DIR.glob("*.zip"), key=lambda x: x.stat().st_mtime, reverse=True):
            linhas.append(
                {
                    "Arquivo": arq.name,
                    "Caminho": str(arq),
                    "Tamanho": _backup_tamanho_formatado(arq.stat().st_size),
                    "Bytes": arq.stat().st_size,
                    "Criado em": datetime.fromtimestamp(arq.stat().st_mtime).strftime("%d/%m/%Y %H:%M:%S")
                }
            )

        return pd.DataFrame(linhas)

    except Exception:
        return pd.DataFrame()


def _backup_ultimo():
    try:
        backups = listar_backups_eirox()
        if backups.empty:
            return None
        return backups.iloc[0].to_dict()
    except Exception:
        return None


def _backup_espaco_total():
    try:
        total = 0
        if not BACKUP_DIR.exists():
            return 0
        for arq in BACKUP_DIR.glob("*.zip"):
            total += arq.stat().st_size
        return total
    except Exception:
        return 0


def limpar_backups_antigos(manter=10):
    try:
        BACKUP_DIR.mkdir(exist_ok=True)
        backups = sorted(
            BACKUP_DIR.glob("*.zip"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        removidos = 0

        for arq in backups[int(manter):]:
            try:
                arq.unlink()
                removidos += 1
            except Exception:
                pass

        return removidos

    except Exception:
        return 0



# --------------------------------------------------
# SAÚDE DO SISTEMA - HOMOLOGAÇÃO v1.35.3
# --------------------------------------------------

def _health_numero_br(valor):
    try:
        return f"{int(valor):,}".replace(",", ".")
    except Exception:
        return "0"


def _health_formatar_data(timestamp):
    try:
        return datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return ""


def _health_status_base(qtd_arquivos, ultima_atualizacao):
    try:
        if qtd_arquivos <= 0:
            return "🔴 Não encontrada"

        if ultima_atualizacao:
            dt = datetime.strptime(ultima_atualizacao, "%d/%m/%Y %H:%M:%S")
            dias = (datetime.now() - dt).days
            if dias >= 7:
                return "🟡 Desatualizada"

        return "🟢 OK"
    except Exception:
        return "🟢 OK" if qtd_arquivos > 0 else "🔴 Não encontrada"


def _health_ler_amostra_arquivo(arquivo):
    try:
        if arquivo.suffix.lower() == ".csv":
            try:
                return pd.read_csv(arquivo, sep=";", encoding="utf-8-sig")
            except Exception:
                return pd.read_csv(arquivo, encoding="utf-8-sig")
        return pd.read_excel(arquivo)
    except Exception:
        return pd.DataFrame()


def _health_analisar_pasta(nome_base, caminhos):
    inicio = time.time()
    arquivos = []

    for caminho in caminhos:
        p = Path(caminho)
        if p.exists() and p.is_dir():
            for ext in ["*.xlsx", "*.xls", "*.xlsm", "*.csv"]:
                arquivos.extend(list(p.glob(ext)))
        elif p.exists() and p.is_file():
            arquivos.append(p)

    arquivos = sorted(set(arquivos), key=lambda x: str(x))

    total_registros = 0
    erros = []
    ultima_ts = None

    for arquivo in arquivos:
        try:
            ultima_ts_arq = arquivo.stat().st_mtime
            if ultima_ts is None or ultima_ts_arq > ultima_ts:
                ultima_ts = ultima_ts_arq

            temp = _health_ler_amostra_arquivo(arquivo)
            if isinstance(temp, pd.DataFrame) and not temp.empty:
                total_registros += len(temp)
        except Exception as erro:
            erros.append(f"{arquivo.name}: {erro}")

    ultima_atualizacao = _health_formatar_data(ultima_ts) if ultima_ts else ""
    tempo = round(time.time() - inicio, 2)

    return {
        "Base": nome_base,
        "Status": _health_status_base(len(arquivos), ultima_atualizacao),
        "Arquivos": len(arquivos),
        "Registros": total_registros,
        "Última Atualização": ultima_atualizacao,
        "Tempo Leitura (s)": tempo,
        "Caminhos": ", ".join([str(a) for a in arquivos[:5]]),
        "Erros": " | ".join(erros[:5])
    }


@st.cache_data(ttl=120, show_spinner=False)
def gerar_saude_bases():
    bases = [
        ("VENDA_TESTE", ["VENDA_TESTE", "VENDA_TESTE.zip"]),
        ("VENDA_FINAL_TESTE", ["VENDA_FINAL_TESTE", "VENDA_TESTE_FINAL", "VENDA_FINAL", "VENDA_REDE", "VENDA_FINAL_TESTE.zip", "VENDA_TESTE_FINAL.zip", "VENDA_FINAL.zip"]),
        ("COMPRA_TESTE", ["COMPRA_TESTE", "COMPRA", "COMPRAS_TESTE", "COMPRA_TESTE.zip", "COMPRA.zip"]),
        ("ESTOQUE_TESTE", ["ESTOQUE_TESTE", "ESTOQUE", "ESTOQUE_TESTE.zip", "ESTOQUE.zip"]),
        ("Analise_Pricing.xlsx", ["Analise_Pricing.xlsx"])
    ]
    return pd.DataFrame([_health_analisar_pasta(nome, caminhos) for nome, caminhos in bases])


def diagnostico_integridade_basico():
    checks = []
    try:
        bases_memoria = {
            "Analise_Pricing": df if "df" in globals() else pd.DataFrame(),
            "VENDA_TESTE": historico if "historico" in globals() else pd.DataFrame(),
            "VENDA_FINAL_TESTE": venda_rede if "venda_rede" in globals() else pd.DataFrame(),
            "COMPRA_TESTE": compra if "compra" in globals() else pd.DataFrame(),
            "ESTOQUE_TESTE": estoque if "estoque" in globals() else pd.DataFrame()
        }

        for nome, base in bases_memoria.items():
            if not isinstance(base, pd.DataFrame) or base.empty:
                checks.append({"Base": nome, "Verificação": "Base carregada", "Status": "🔴 Erro", "Ocorrências": 0, "Detalhe": "Base vazia ou não carregada."})
                continue

            checks.append({"Base": nome, "Verificação": "Base carregada", "Status": "🟢 OK", "Ocorrências": len(base), "Detalhe": "Base disponível em memória."})

            colunas = base.columns.astype(str).tolist()

            col_ean = None
            for c in colunas:
                if str(c).strip().lower() in ["ean", "ean (gtin)", "gtin", "cód. barras/etiq.", "cod. barras/etiq.", "codigo de barras", "código de barras"]:
                    col_ean = c
                    break

            col_produto = None
            for c in colunas:
                if "produto" in str(c).lower() or "descr" in str(c).lower():
                    col_produto = c
                    break

            col_preco = None
            for c in colunas:
                if "preço" in str(c).lower() or "preco" in str(c).lower() or "valor" in str(c).lower():
                    col_preco = c
                    break

            if col_ean:
                serie_ean = base[col_ean].astype(str).str.strip()
                vazios = int(serie_ean.isin(["", "nan", "None"]).sum())
                checks.append({"Base": nome, "Verificação": "EAN vazio", "Status": "🟢 OK" if vazios == 0 else "🟡 Atenção", "Ocorrências": vazios, "Detalhe": f"Coluna analisada: {col_ean}"})

                duplicados = int(serie_ean.duplicated().sum())
                checks.append({"Base": nome, "Verificação": "EAN duplicado", "Status": "🟢 OK" if duplicados == 0 else "🟡 Atenção", "Ocorrências": duplicados, "Detalhe": f"Coluna analisada: {col_ean}"})

            if col_produto:
                vazios_prod = int(base[col_produto].astype(str).str.strip().isin(["", "nan", "None"]).sum())
                checks.append({"Base": nome, "Verificação": "Produto/descrição vazio", "Status": "🟢 OK" if vazios_prod == 0 else "🟡 Atenção", "Ocorrências": vazios_prod, "Detalhe": f"Coluna analisada: {col_produto}"})

            if col_preco:
                if "converter_numero_brasil" in globals():
                    serie = converter_numero_brasil(base[col_preco])
                else:
                    serie = pd.to_numeric(base[col_preco], errors="coerce")
                zerados = int((serie.fillna(0) <= 0).sum())
                checks.append({"Base": nome, "Verificação": "Preço/valor zerado ou inválido", "Status": "🟢 OK" if zerados == 0 else "🟡 Atenção", "Ocorrências": zerados, "Detalhe": f"Coluna analisada: {col_preco}"})

    except Exception as erro:
        checks.append({"Base": "Sistema", "Verificação": "Diagnóstico", "Status": "🔴 Erro", "Ocorrências": 1, "Detalhe": str(erro)})

    return pd.DataFrame(checks)


def health_status_telegram():
    try:
        token = obter_config_telegram("TELEGRAM_BOT_TOKEN") if "obter_config_telegram" in globals() else ""
        chat = obter_config_telegram("TELEGRAM_CHAT_ID") if "obter_config_telegram" in globals() else ""
        return "🟢 Configurado" if token and chat else "🟡 Não configurado"
    except Exception:
        return "🔴 Erro"


def health_status_usuarios():
    try:
        if "carregar_usuarios_sistema" in globals():
            base = carregar_usuarios_sistema()
            total = len(base)
            ativos = int((base["Ativo"].astype(str).str.lower() == "sim").sum()) if not base.empty and "Ativo" in base.columns else 0
            return total, ativos, total - ativos
        return 0, 0, 0
    except Exception:
        return 0, 0, 0


def health_ultimo_login():
    try:
        logs = carregar_logs_acesso() if "carregar_logs_acesso" in globals() else pd.DataFrame()
        if logs.empty or "Evento" not in logs.columns:
            return "-"
        logins = logs[logs["Evento"].astype(str).eq("Login")].copy()
        if logins.empty:
            return "-"
        if "Data_Hora_dt" not in logins.columns:
            logins["Data_Hora_dt"] = pd.to_datetime(logins["Data_Hora"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
        return logins.sort_values("Data_Hora_dt", ascending=False)["Data_Hora"].iloc[0]
    except Exception:
        return "-"




# --------------------------------------------------
# MULTIEMPRESA - HOMOLOGAÇÃO v1.35.5
# --------------------------------------------------

EMPRESAS_ARQUIVO = Path("EMPRESAS_EIROX.csv")


def usuario_master():
    """
    Usuário master da plataforma.
    """

    try:
        return (
            str(st.session_state.get("usuario", ""))
            .strip()
            .lower()
            == "paulomarques"
        )

    except Exception:
        return False


def inicializar_empresas():
    try:
        if not EMPRESAS_ARQUIVO.exists():
            base = pd.DataFrame(
                [
                    {
                        "EmpresaID": "1",
                        "Empresa": "Marabá - Cliente teste",
                        "Ativa": "Sim",
                        "Criado_Em": horario_brasil_formatado() if "horario_brasil_formatado" in globals() else datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    },
                    {
                        "EmpresaID": "2",
                        "Empresa": "Belém - Cliente teste",
                        "Ativa": "Sim",
                        "Criado_Em": horario_brasil_formatado() if "horario_brasil_formatado" in globals() else datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    }
                ]
            )
            base.to_csv(EMPRESAS_ARQUIVO, index=False, sep=";", encoding="utf-8-sig")
        return True
    except Exception:
        return False


@st.cache_data(ttl=60, show_spinner=False)
def carregar_empresas_sistema():
    try:
        inicializar_empresas()
        base = pd.read_csv(EMPRESAS_ARQUIVO, sep=";", encoding="utf-8-sig", dtype=str).fillna("")

        obrigatorias = ["EmpresaID", "Empresa", "Ativa", "Criado_Em"]

        for col in obrigatorias:
            if col not in base.columns:
                base[col] = ""

        base["EmpresaID"] = base["EmpresaID"].astype(str).str.strip()
        base["Empresa"] = base["Empresa"].astype(str).str.strip()
        base["Ativa"] = base["Ativa"].replace("", "Sim")

        return base[obrigatorias].copy()

    except Exception:
        return pd.DataFrame([{"EmpresaID": "1", "Empresa": "Marabá - Cliente teste", "Ativa": "Sim", "Criado_Em": ""}])


def salvar_empresas_sistema(base):
    try:
        base = base.copy()
        base["EmpresaID"] = base["EmpresaID"].astype(str).str.strip()
        base["Empresa"] = base["Empresa"].astype(str).str.strip()
        base.to_csv(EMPRESAS_ARQUIVO, index=False, sep=";", encoding="utf-8-sig")

        try:
            carregar_empresas_sistema.clear()
        except Exception:
            pass

        return True
    except Exception:
        return False


def criar_ou_atualizar_empresa(empresa_id, empresa, ativa="Sim"):
    try:
        empresa_id = str(empresa_id).strip()
        empresa = str(empresa).strip()
        ativa = str(ativa).strip()

        if not empresa_id or not empresa:
            return False, "EmpresaID e nome da empresa são obrigatórios."

        base = carregar_empresas_sistema()

        if empresa_id in base["EmpresaID"].astype(str).tolist():
            idx = base.index[base["EmpresaID"].astype(str) == empresa_id][0]
            base.loc[idx, "Empresa"] = empresa
            base.loc[idx, "Ativa"] = ativa
            acao = "Atualização de empresa"
        else:
            nova = pd.DataFrame(
                [
                    {
                        "EmpresaID": empresa_id,
                        "Empresa": empresa,
                        "Ativa": ativa,
                        "Criado_Em": horario_brasil_formatado() if "horario_brasil_formatado" in globals() else datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    }
                ]
            )
            base = pd.concat([base, nova], ignore_index=True)
            acao = "Criação de empresa"

        salvar_empresas_sistema(base)

        try:
            registrar_log_usuario(acao, empresa_id, f"Empresa: {empresa} | Ativa: {ativa}")
        except Exception:
            pass

        return True, f"{acao} realizada com sucesso."

    except Exception as erro:
        return False, f"Erro ao salvar empresa: {erro}"


def obter_nome_empresa(empresa_id):
    try:
        empresa_id = str(empresa_id).strip()
        empresas = carregar_empresas_sistema()
        linha = empresas[empresas["EmpresaID"].astype(str).str.strip() == empresa_id]

        if linha.empty:
            return "Empresa não identificada"

        return str(linha.iloc[0]["Empresa"])

    except Exception:
        return "Empresa não identificada"


def empresa_usuario_logado():
    try:
        empresa_id = str(st.session_state.get("empresa_id_usuario", "1")).strip()
        return empresa_id if empresa_id else "1"
    except Exception:
        return "1"


def empresa_contexto_atual():
    try:
        if usuario_master():
            return str(st.session_state.get("empresa_id_contexto", empresa_usuario_logado())).strip()
        return empresa_usuario_logado()
    except Exception:
        return "1"


def aplicar_filtro_empresa(base):
    try:
        if not isinstance(base, pd.DataFrame) or base.empty:
            return base
        if "EmpresaID" not in base.columns:
            return base
        empresa_id = empresa_contexto_atual()
        return base[base["EmpresaID"].astype(str).str.strip() == str(empresa_id)].copy()
    except Exception:
        return base


def preparar_base_usuarios_multiempresa():
    try:
        if "carregar_usuarios_sistema" not in globals() or "salvar_usuarios_sistema" not in globals():
            return

        base = carregar_usuarios_sistema()

        if "EmpresaID" not in base.columns:
            base["EmpresaID"] = "1"

            if "Usuario" in base.columns:
                base.loc[
                    base["Usuario"].astype(str).str.lower().eq("paulomarques"),
                    "EmpresaID"
                ] = "1"

            salvar_usuarios_sistema(base)

    except Exception:
        pass


def usuario_pode_ver_multiempresa():
    return usuario_master()




# --------------------------------------------------
# EXPERIÊNCIA ENTERPRISE - SUBTÍTULOS E AJUDA
# --------------------------------------------------

DESCRICOES_TELAS_ENTERPRISE = {
    "📊 Dashboard Geral": "Visão consolidada dos principais indicadores de pricing, margem, lucratividade e competitividade.",
    "📊 Painel Geral": "Visão consolidada dos principais indicadores de pricing, margem, lucratividade e competitividade.",
    "🔎 Rede/Loja vs Concorrentes": "Comparativo detalhado entre preços praticados pela rede e seus principais concorrentes.",
    "🔍 Rede/Loja vs Concorrentes": "Comparativo detalhado entre preços praticados pela rede e seus principais concorrentes.",
    "📈 Evolução Histórica": "Acompanhamento da evolução dos preços ao longo do tempo por produto e farmácia.",
    "🗺️ Mapa Farmácias": "Distribuição geográfica das farmácias pesquisadas e análise regional de preços.",
    "🧠 Simulador Inteligente": "Simule cenários de preço, margem e competitividade antes de tomar decisões comerciais.",
    "👥 Controle de Usuários": "Gerenciamento de acessos, permissões, bloqueios, expiração de senha e políticas de segurança.",
    "🔐 Central de Auditoria": "Monitoramento completo dos acessos, navegação e atividades realizadas pelos usuários.",
    "🟢 Saúde do Sistema": "Monitoramento operacional do ambiente, performance, integridade das bases e integrações.",
    "📦 Backup Center": "Gerenciamento de backups, restauração e proteção das informações críticas do sistema.",
    "🏢 Multiempresa": "Administração de empresas, segregação de dados e preparação do ambiente SaaS.",
    "📌 Sobre o Eirox": "Informações institucionais, propósito da plataforma e visão geral do produto.",
    "🧭 Roadmap do Produto": "Plano evolutivo da plataforma, módulos concluídos, próximos ciclos e prioridades.",
    "💼 Licenciamento Multiempresa": "Modelo comercial, planos de uso, governança de clientes e expansão SaaS.",
    "💼 Licenciamento Real": "Controle real de planos, expiração, limites de usuários, lojas e bloqueio de licença.",
    "🚨 Alertas Inteligentes": "Monitoramento automático de riscos e oportunidades comerciais com envio via Telegram.",
    "💰 Motor de Oportunidades": "Ranking financeiro das maiores oportunidades de ganho por produto, laboratório, categoria e loja."
}


def legenda_tela(titulo, texto=None):
    try:
        descricao = texto or DESCRICOES_TELAS_ENTERPRISE.get(titulo, "")
        if descricao:
            st.caption(f"ⓘ {descricao}")
    except Exception:
        pass


def card_enterprise(titulo, descricao, icone="ⓘ"):
    st.markdown(
        f"""
        <div class="eirox-card">
            <div class="eirox-section-title">{icone} {titulo}</div>
            <p>{descricao}</p>
        </div>
        """,
        unsafe_allow_html=True
    )




# --------------------------------------------------
# LICENCIAMENTO REAL - v1.36.0
# --------------------------------------------------

LICENCAS_ARQUIVO = Path("LICENCAS_EIROX.csv")


PLANOS_EIROX = {
    "Starter": {
        "MaxUsuarios": 5,
        "MaxLojas": 10,
        "Modulos": "Dashboard + Concorrência"
    },
    "Professional": {
        "MaxUsuarios": 20,
        "MaxLojas": 50,
        "Modulos": "Dashboard + Concorrência + Simulador + Auditoria"
    },
    "Enterprise": {
        "MaxUsuarios": 100,
        "MaxLojas": 500,
        "Modulos": "Todos os módulos"
    },
    "Enterprise Plus": {
        "MaxUsuarios": 9999,
        "MaxLojas": 9999,
        "Modulos": "Todos + APIs + IA Pricing"
    }
}


def inicializar_licencas():
    """
    Cria base inicial de licenças.
    """

    try:
        if not LICENCAS_ARQUIVO.exists():

            hoje = datetime.now(ZoneInfo("America/Sao_Paulo"))

            base = pd.DataFrame(
                [
                    {
                        "EmpresaID": "1",
                        "Empresa": "Marabá - Cliente teste",
                        "Plano": "Enterprise",
                        "DataInicio": hoje.strftime("%d/%m/%Y"),
                        "DataExpiracao": (hoje + pd.DateOffset(years=1)).strftime("%d/%m/%Y"),
                        "MaxUsuarios": str(PLANOS_EIROX["Enterprise"]["MaxUsuarios"]),
                        "MaxLojas": str(PLANOS_EIROX["Enterprise"]["MaxLojas"]),
                        "Status": "Ativa",
                        "Observacao": "Licença inicial de homologação"
                    },
                    {
                        "EmpresaID": "2",
                        "Empresa": "Belém - Cliente teste",
                        "Plano": "Starter",
                        "DataInicio": hoje.strftime("%d/%m/%Y"),
                        "DataExpiracao": (hoje + pd.DateOffset(days=30)).strftime("%d/%m/%Y"),
                        "MaxUsuarios": str(PLANOS_EIROX["Starter"]["MaxUsuarios"]),
                        "MaxLojas": str(PLANOS_EIROX["Starter"]["MaxLojas"]),
                        "Status": "Trial",
                        "Observacao": "Cliente teste"
                    }
                ]
            )

            base.to_csv(
                LICENCAS_ARQUIVO,
                index=False,
                sep=";",
                encoding="utf-8-sig"
            )

        return True

    except Exception:
        return False


@st.cache_data(ttl=60, show_spinner=False)
def carregar_licencas_sistema():
    """
    Carrega licenças cadastradas.
    """

    try:
        inicializar_licencas()

        base = pd.read_csv(
            LICENCAS_ARQUIVO,
            sep=";",
            encoding="utf-8-sig",
            dtype=str
        ).fillna("")

        obrigatorias = [
            "EmpresaID",
            "Empresa",
            "Plano",
            "DataInicio",
            "DataExpiracao",
            "MaxUsuarios",
            "MaxLojas",
            "Status",
            "Observacao"
        ]

        for col in obrigatorias:
            if col not in base.columns:
                base[col] = ""

        base["EmpresaID"] = base["EmpresaID"].astype(str).str.strip()
        base["Empresa"] = base["Empresa"].astype(str).str.strip()
        base["Plano"] = base["Plano"].replace("", "Starter")
        base["Status"] = base["Status"].replace("", "Ativa")

        return base[obrigatorias].copy()

    except Exception:
        return pd.DataFrame()


def salvar_licencas_sistema(base):
    """
    Salva base de licenças.
    """

    try:
        base = base.copy()
        base = base.astype(str)
        base["EmpresaID"] = base["EmpresaID"].astype(str).str.strip()

        base.to_csv(
            LICENCAS_ARQUIVO,
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        try:
            carregar_licencas_sistema.clear()
        except Exception:
            pass

        return True

    except Exception:
        return False


def obter_licenca_empresa(empresa_id):
    """
    Retorna licença da empresa.
    """

    try:
        empresa_id = str(empresa_id).strip()
        licencas = carregar_licencas_sistema()

        linha = licencas[
            licencas["EmpresaID"].astype(str).str.strip() == empresa_id
        ]

        if linha.empty:
            return None

        return linha.iloc[0].to_dict()

    except Exception:
        return None


def dias_restantes_licenca(data_expiracao):
    """
    Calcula dias restantes da licença.
    """

    try:
        data_exp = pd.to_datetime(
            str(data_expiracao),
            dayfirst=True,
            errors="coerce"
        )

        if pd.isna(data_exp):
            return None

        hoje = pd.Timestamp.now().normalize()

        return int((data_exp.normalize() - hoje).days)

    except Exception:
        return None


def status_licenca_empresa(empresa_id):
    """
    Status operacional da licença.
    """

    try:
        lic = obter_licenca_empresa(empresa_id)

        if not lic:
            return {
                "StatusOperacional": "🔴 Sem licença",
                "Bloqueada": True,
                "DiasRestantes": None,
                "Mensagem": "Empresa sem licença cadastrada."
            }

        status = str(lic.get("Status", "")).strip()
        dias = dias_restantes_licenca(lic.get("DataExpiracao", ""))

        if status.lower() in ["bloqueada", "inativa", "cancelada"]:
            return {
                "StatusOperacional": "🔴 Bloqueada",
                "Bloqueada": True,
                "DiasRestantes": dias,
                "Mensagem": "Licença bloqueada ou inativa."
            }

        if dias is not None and dias < 0:
            return {
                "StatusOperacional": "🔴 Expirada",
                "Bloqueada": True,
                "DiasRestantes": dias,
                "Mensagem": "Licença expirada."
            }

        if status.lower() == "trial":
            return {
                "StatusOperacional": "🟡 Trial",
                "Bloqueada": False,
                "DiasRestantes": dias,
                "Mensagem": "Licença em período de teste."
            }

        if dias is not None and dias <= 15:
            return {
                "StatusOperacional": "🟡 Próxima do vencimento",
                "Bloqueada": False,
                "DiasRestantes": dias,
                "Mensagem": "Licença próxima do vencimento."
            }

        return {
            "StatusOperacional": "🟢 Ativa",
            "Bloqueada": False,
            "DiasRestantes": dias,
            "Mensagem": "Licença ativa."
        }

    except Exception as erro:
        return {
            "StatusOperacional": "🔴 Erro",
            "Bloqueada": True,
            "DiasRestantes": None,
            "Mensagem": str(erro)
        }


def validar_licenca_login(usuario):
    """
    Valida licença no login.
    paulomarques não é bloqueado para suporte master.
    """

    try:
        usuario = str(usuario).strip().lower()

        if usuario in ["paulomarques"]:
            return True, ""

        dados = obter_dados_usuario(usuario) if "obter_dados_usuario" in globals() else None

        empresa_id = "1"

        if dados:
            empresa_id = str(dados.get("EmpresaID", "1")).strip() or "1"

        status = status_licenca_empresa(empresa_id)

        if status.get("Bloqueada"):
            return False, f"{status.get('StatusOperacional')} - {status.get('Mensagem')}"

        return True, ""

    except Exception:
        return True, ""


def contar_usuarios_empresa(empresa_id):
    """
    Conta usuários vinculados à empresa.
    """

    try:
        if "carregar_usuarios_sistema" not in globals():
            return 0

        usuarios = carregar_usuarios_sistema()

        if usuarios.empty:
            return 0

        if "EmpresaID" not in usuarios.columns:
            usuarios["EmpresaID"] = "1"

        return int(
            usuarios[
                usuarios["EmpresaID"].astype(str).str.strip() == str(empresa_id).strip()
            ]["Usuario"].nunique()
        )

    except Exception:
        return 0


def contar_lojas_empresa(empresa_id):
    """
    Conta lojas quando houver colunas compatíveis.
    Se a base ainda não tiver EmpresaID, calcula de forma geral para compatibilidade.
    """

    try:
        bases = []

        for nome_var in ["df", "venda_rede", "historico"]:
            base = globals().get(nome_var, pd.DataFrame())

            if isinstance(base, pd.DataFrame) and not base.empty:
                temp = base.copy()

                if "EmpresaID" in temp.columns:
                    temp = temp[
                        temp["EmpresaID"].astype(str).str.strip() == str(empresa_id).strip()
                    ]

                bases.append(temp)

        if not bases:
            return 0

        base_all = pd.concat(bases, ignore_index=True)

        col_loja = None

        for c in base_all.columns:
            nome = str(c).lower()
            if nome in ["loja", "filial", "cod_loja", "codigo loja", "código loja"] or "loja" in nome or "filial" in nome:
                col_loja = c
                break

        if col_loja:
            return int(base_all[col_loja].astype(str).nunique())

        col_farmacia = None

        for c in base_all.columns:
            nome = str(c).lower()
            if "farmácia" in nome or "farmacia" in nome:
                col_farmacia = c
                break

        if col_farmacia:
            return int(base_all[col_farmacia].astype(str).nunique())

        return 0

    except Exception:
        return 0


def licenca_metricas_empresa(empresa_id):
    """
    Métricas completas de licença.
    """

    try:
        lic = obter_licenca_empresa(empresa_id) or {}
        status = status_licenca_empresa(empresa_id)

        max_usuarios = int(float(str(lic.get("MaxUsuarios", 0)).replace(",", ".") or 0))
        max_lojas = int(float(str(lic.get("MaxLojas", 0)).replace(",", ".") or 0))

        usuarios_usados = contar_usuarios_empresa(empresa_id)
        lojas_usadas = contar_lojas_empresa(empresa_id)

        return {
            "Licenca": lic,
            "Status": status,
            "MaxUsuarios": max_usuarios,
            "MaxLojas": max_lojas,
            "UsuariosUsados": usuarios_usados,
            "LojasUsadas": lojas_usadas,
            "UsuariosDisponiveis": max(max_usuarios - usuarios_usados, 0),
            "LojasDisponiveis": max(max_lojas - lojas_usadas, 0)
        }

    except Exception:
        return {
            "Licenca": {},
            "Status": {},
            "MaxUsuarios": 0,
            "MaxLojas": 0,
            "UsuariosUsados": 0,
            "LojasUsadas": 0,
            "UsuariosDisponiveis": 0,
            "LojasDisponiveis": 0
        }


def criar_ou_atualizar_licenca(empresa_id, empresa, plano, data_inicio, data_expiracao, status, observacao=""):
    """
    Cria ou atualiza licença.
    """

    try:
        empresa_id = str(empresa_id).strip()
        empresa = str(empresa).strip()
        plano = str(plano).strip()
        status = str(status).strip()

        if not empresa_id or not empresa or not plano:
            return False, "EmpresaID, Empresa e Plano são obrigatórios."

        plano_info = PLANOS_EIROX.get(plano, PLANOS_EIROX["Starter"])

        base = carregar_licencas_sistema()

        if empresa_id in base["EmpresaID"].astype(str).tolist():
            idx = base.index[base["EmpresaID"].astype(str) == empresa_id][0]

            base.loc[idx, "Empresa"] = empresa
            base.loc[idx, "Plano"] = plano
            base.loc[idx, "DataInicio"] = data_inicio
            base.loc[idx, "DataExpiracao"] = data_expiracao
            base.loc[idx, "MaxUsuarios"] = str(plano_info["MaxUsuarios"])
            base.loc[idx, "MaxLojas"] = str(plano_info["MaxLojas"])
            base.loc[idx, "Status"] = status
            base.loc[idx, "Observacao"] = observacao

            acao = "Atualização de licença"

        else:
            nova = pd.DataFrame(
                [
                    {
                        "EmpresaID": empresa_id,
                        "Empresa": empresa,
                        "Plano": plano,
                        "DataInicio": data_inicio,
                        "DataExpiracao": data_expiracao,
                        "MaxUsuarios": str(plano_info["MaxUsuarios"]),
                        "MaxLojas": str(plano_info["MaxLojas"]),
                        "Status": status,
                        "Observacao": observacao
                    }
                ]
            )

            base = pd.concat(
                [
                    base,
                    nova
                ],
                ignore_index=True
            )

            acao = "Criação de licença"

        salvar_licencas_sistema(base)

        try:
            registrar_log_usuario(
                acao,
                empresa_id,
                f"Empresa={empresa} | Plano={plano} | Status={status} | Expiração={data_expiracao}"
            )
        except Exception:
            pass

        try:
            enviar_alerta_telegram(
                "💼 <b>Licença Eirox atualizada</b>\n\n"
                f"🏢 <b>Empresa:</b> {empresa}\n"
                f"📦 <b>Plano:</b> {plano}\n"
                f"📅 <b>Expiração:</b> {data_expiracao}\n"
                f"🔐 <b>Status:</b> {status}\n"
                f"👤 <b>Usuário:</b> {st.session_state.get('usuario', '')}\n"
                f"🏷️ <b>Versão:</b> {VERSAO_APP}"
            )
        except Exception:
            pass

        return True, f"{acao} realizada com sucesso."

    except Exception as erro:
        return False, f"Erro ao salvar licença: {erro}"


def usuario_pode_ver_licenciamento_real():
    try:
        return usuario_master() if "usuario_master" in globals() else str(st.session_state.get("usuario", "")).lower() == "paulomarques"
    except Exception:
        return False




# --------------------------------------------------
# ALERTAS INTELIGENTES - v1.36.1
# --------------------------------------------------

ALERTAS_ARQUIVO = Path("ALERTAS_EIROX.csv")


def _alerta_numero_br(valor, casas=2):
    try:
        return f"{float(valor):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00"


def _alerta_data_hora():
    try:
        return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def _alerta_salvar(alertas):
    try:
        if not alertas:
            return

        novos = pd.DataFrame(alertas)

        if ALERTAS_ARQUIVO.exists():
            antigo = pd.read_csv(ALERTAS_ARQUIVO, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
            final = pd.concat([antigo, novos], ignore_index=True)
        else:
            final = novos

        final.to_csv(ALERTAS_ARQUIVO, index=False, sep=";", encoding="utf-8-sig")

    except Exception:
        pass


def carregar_historico_alertas():
    try:
        if not ALERTAS_ARQUIVO.exists():
            return pd.DataFrame()

        return pd.read_csv(ALERTAS_ARQUIVO, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
    except Exception:
        return pd.DataFrame()


def _alerta_coluna(base, possibilidades):
    try:
        cols = list(base.columns)

        for alvo in possibilidades:
            alvo_norm = str(alvo).strip().lower()
            for c in cols:
                if str(c).strip().lower() == alvo_norm:
                    return c

        for alvo in possibilidades:
            alvo_norm = str(alvo).strip().lower()
            for c in cols:
                if alvo_norm in str(c).strip().lower():
                    return c

        return None
    except Exception:
        return None


def _alerta_converter_numero(serie):
    try:
        if "converter_numero_brasil" in globals():
            return converter_numero_brasil(serie)

        return pd.to_numeric(
            serie.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
            errors="coerce"
        )
    except Exception:
        return pd.to_numeric(serie, errors="coerce")


def gerar_alertas_inteligentes(limite_margem=20, limite_diferenca_concorrente=10, dias_sem_pesquisa=7, limite_estoque_alto=50, limite_alertas=100):
    alertas = []

    try:
        base = globals().get("df", pd.DataFrame())

        if not isinstance(base, pd.DataFrame) or base.empty:
            base = globals().get("base_pesquisa", pd.DataFrame())

        if not isinstance(base, pd.DataFrame) or base.empty:
            return pd.DataFrame()

        base = base.copy()

        try:
            if "aplicar_filtro_empresa" in globals():
                base = aplicar_filtro_empresa(base)
        except Exception:
            pass

        empresa_id = empresa_contexto_atual() if "empresa_contexto_atual" in globals() else "1"
        empresa_nome = obter_nome_empresa(empresa_id) if "obter_nome_empresa" in globals() else ""

        col_ean = _alerta_coluna(base, ["EAN", "EAN (GTIN)", "GTIN", "Código de Barras"])
        col_prod = _alerta_coluna(base, ["Produto", "Produto_Base_SIM", "Descrição", "Descricao"])
        col_margem = _alerta_coluna(base, ["Margem_%", "Margem", "Margem %"])
        col_preco_rede = _alerta_coluna(base, ["Preco_Rede", "Preço Rede", "Preco Loja", "Preço Loja", "Preco_Venda", "Preço (R$)"])
        col_preco_conc = _alerta_coluna(base, ["Menor_Preco_Concorrente", "Menor Concorrente", "Preco_Concorrente", "Preço Concorrente", "Menor_Preco"])
        col_estoque = _alerta_coluna(base, ["Estoque", "Estoque Atual", "Qtde Estoque", "Quantidade Estoque"])
        col_data = _alerta_coluna(base, ["Data", "Data Pesquisa", "Data_Pesquisa", "Última Pesquisa", "Ultima Pesquisa"])
        col_ganho = _alerta_coluna(base, ["Ganho_Potencial", "Potencial de Captura", "Oportunidade"])

        if col_margem:
            margem = _alerta_converter_numero(base[col_margem])
            temp = base[margem < float(limite_margem)].copy()
            temp["_valor_alerta"] = margem[margem < float(limite_margem)]

            for _, row in temp.head(limite_alertas).iterrows():
                alertas.append({
                    "Data_Hora": _alerta_data_hora(),
                    "EmpresaID": empresa_id,
                    "Empresa": empresa_nome,
                    "Tipo": "Margem abaixo da meta",
                    "Severidade": "Alta",
                    "EAN": str(row.get(col_ean, "")) if col_ean else "",
                    "Produto": str(row.get(col_prod, "")) if col_prod else "",
                    "Valor": _alerta_numero_br(row.get("_valor_alerta", "")),
                    "Regra": f"Margem menor que {limite_margem}%",
                    "Ação Sugerida": "Revisar preço, custo ou negociação de compra."
                })

        if col_preco_rede and col_preco_conc:
            preco_rede = _alerta_converter_numero(base[col_preco_rede])
            preco_conc = _alerta_converter_numero(base[col_preco_conc])
            dif = ((preco_rede - preco_conc) / preco_rede.replace(0, pd.NA)) * 100
            mask = (preco_rede > 0) & (preco_conc > 0) & (dif > float(limite_diferenca_concorrente))

            temp = base[mask].copy()
            temp["_dif_alerta"] = dif[mask]

            for _, row in temp.head(limite_alertas).iterrows():
                alertas.append({
                    "Data_Hora": _alerta_data_hora(),
                    "EmpresaID": empresa_id,
                    "Empresa": empresa_nome,
                    "Tipo": "Concorrente mais barato",
                    "Severidade": "Alta",
                    "EAN": str(row.get(col_ean, "")) if col_ean else "",
                    "Produto": str(row.get(col_prod, "")) if col_prod else "",
                    "Valor": f"{_alerta_numero_br(row.get('_dif_alerta', ''))}%",
                    "Regra": f"Concorrente mais barato acima de {limite_diferenca_concorrente}%",
                    "Ação Sugerida": "Avaliar ajuste de preço ou estratégia por curva/margem."
                })

        if col_data:
            datas = pd.to_datetime(base[col_data], dayfirst=True, errors="coerce")
            dias = (pd.Timestamp.now().normalize() - datas.dt.normalize()).dt.days
            mask = dias > int(dias_sem_pesquisa)

            temp = base[mask].copy()
            temp["_dias_alerta"] = dias[mask]

            for _, row in temp.head(limite_alertas).iterrows():
                valor = row.get("_dias_alerta", 0)
                alertas.append({
                    "Data_Hora": _alerta_data_hora(),
                    "EmpresaID": empresa_id,
                    "Empresa": empresa_nome,
                    "Tipo": "Produto sem pesquisa recente",
                    "Severidade": "Média",
                    "EAN": str(row.get(col_ean, "")) if col_ean else "",
                    "Produto": str(row.get(col_prod, "")) if col_prod else "",
                    "Valor": f"{int(valor) if pd.notna(valor) else 0} dias",
                    "Regra": f"Sem pesquisa há mais de {dias_sem_pesquisa} dias",
                    "Ação Sugerida": "Incluir produto na próxima sugestão de pesquisa."
                })

        if col_estoque and col_margem:
            estoque = _alerta_converter_numero(base[col_estoque])
            margem = _alerta_converter_numero(base[col_margem])
            mask = (estoque >= float(limite_estoque_alto)) & (margem < float(limite_margem))

            temp = base[mask].copy()
            temp["_estoque_alerta"] = estoque[mask]

            for _, row in temp.head(limite_alertas).iterrows():
                alertas.append({
                    "Data_Hora": _alerta_data_hora(),
                    "EmpresaID": empresa_id,
                    "Empresa": empresa_nome,
                    "Tipo": "Estoque alto com margem baixa",
                    "Severidade": "Alta",
                    "EAN": str(row.get(col_ean, "")) if col_ean else "",
                    "Produto": str(row.get(col_prod, "")) if col_prod else "",
                    "Valor": _alerta_numero_br(row.get("_estoque_alerta", ""), 0),
                    "Regra": f"Estoque >= {limite_estoque_alto} e margem < {limite_margem}%",
                    "Ação Sugerida": "Avaliar promoção, negociação ou reposicionamento de preço."
                })

        if col_ganho:
            ganho = _alerta_converter_numero(base[col_ganho])
            limite_ganho = ganho.quantile(0.90) if ganho.notna().sum() > 10 else ganho.mean()

            if pd.notna(limite_ganho) and limite_ganho > 0:
                temp = base[ganho >= limite_ganho].copy()
                temp["_ganho_alerta"] = ganho[ganho >= limite_ganho]

                for _, row in temp.head(limite_alertas).iterrows():
                    alertas.append({
                        "Data_Hora": _alerta_data_hora(),
                        "EmpresaID": empresa_id,
                        "Empresa": empresa_nome,
                        "Tipo": "Alta oportunidade de ganho",
                        "Severidade": "Média",
                        "EAN": str(row.get(col_ean, "")) if col_ean else "",
                        "Produto": str(row.get(col_prod, "")) if col_prod else "",
                        "Valor": f"R$ {_alerta_numero_br(row.get('_ganho_alerta', ''))}",
                        "Regra": "Produto no top 10% de ganho potencial",
                        "Ação Sugerida": "Priorizar na análise comercial e no simulador."
                    })

        alertas_df = pd.DataFrame(alertas)

        if not alertas_df.empty:
            alertas_df = alertas_df.drop_duplicates(subset=["EmpresaID", "Tipo", "EAN", "Produto"], keep="first").head(limite_alertas)

        return alertas_df

    except Exception as erro:
        return pd.DataFrame([{
            "Data_Hora": _alerta_data_hora(),
            "EmpresaID": empresa_contexto_atual() if "empresa_contexto_atual" in globals() else "1",
            "Empresa": "",
            "Tipo": "Erro ao gerar alertas",
            "Severidade": "Alta",
            "EAN": "",
            "Produto": "",
            "Valor": "",
            "Regra": "Falha no motor de alertas",
            "Ação Sugerida": str(erro)
        }])


def enviar_alertas_telegram(alertas_df, limite_envio=10):
    try:
        if alertas_df is None or alertas_df.empty:
            return False, "Nenhum alerta para enviar."

        top = alertas_df.head(int(limite_envio))
        linhas = []

        for _, row in top.iterrows():
            linhas.append(f"• <b>{row.get('Tipo', '')}</b> | {row.get('Produto', '')} | {row.get('Valor', '')}")

        mensagem = (
            "🚨 <b>Alertas Inteligentes Eirox</b>\n\n"
            f"🏢 <b>Empresa:</b> {top.iloc[0].get('Empresa', '')}\n"
            f"📊 <b>Total gerado:</b> {len(alertas_df)}\n"
            f"🕒 <b>Horário:</b> {_alerta_data_hora()}\n\n"
            + "\n".join(linhas[:limite_envio])
            + f"\n\n🏷️ <b>Versão:</b> {VERSAO_APP}"
        )

        ok = enviar_alerta_telegram(mensagem) if "enviar_alerta_telegram" in globals() else False
        return bool(ok), "Alertas enviados ao Telegram." if ok else "Não foi possível enviar ao Telegram."

    except Exception as erro:
        return False, str(erro)


def usuario_pode_ver_alertas_inteligentes():
    try:
        return usuario_master() or tela_liberada_por_plano("🚨 Alertas Inteligentes")
    except Exception:
        return False

# --------------------------------------------------
# MOTOR DE OPORTUNIDADES - v1.36.2
# --------------------------------------------------

OPORTUNIDADES_ARQUIVO = Path("OPORTUNIDADES_EIROX.csv")


def _oport_numero_br(valor, casas=2):
    try:
        return f"{float(valor):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00"


def _oport_data_hora():
    try:
        return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def _oport_coluna(base, possibilidades):
    try:
        cols = list(base.columns)
        for alvo in possibilidades:
            alvo_norm = str(alvo).strip().lower()
            for c in cols:
                if str(c).strip().lower() == alvo_norm:
                    return c
        for alvo in possibilidades:
            alvo_norm = str(alvo).strip().lower()
            for c in cols:
                if alvo_norm in str(c).strip().lower():
                    return c
        return None
    except Exception:
        return None


def _oport_converter_numero(serie):
    try:
        if "converter_numero_brasil" in globals():
            return converter_numero_brasil(serie)
        return pd.to_numeric(serie.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False), errors="coerce")
    except Exception:
        return pd.to_numeric(serie, errors="coerce")


def carregar_historico_oportunidades():
    try:
        if not OPORTUNIDADES_ARQUIVO.exists():
            return pd.DataFrame()
        return pd.read_csv(OPORTUNIDADES_ARQUIVO, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
    except Exception:
        return pd.DataFrame()


def salvar_oportunidades(oportunidades_df):
    try:
        if oportunidades_df is None or oportunidades_df.empty:
            return
        salvar = oportunidades_df.copy()
        salvar["Data_Hora"] = _oport_data_hora()
        if OPORTUNIDADES_ARQUIVO.exists():
            antigo = pd.read_csv(OPORTUNIDADES_ARQUIVO, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
            final = pd.concat([antigo, salvar], ignore_index=True)
        else:
            final = salvar
        final.to_csv(OPORTUNIDADES_ARQUIVO, index=False, sep=";", encoding="utf-8-sig")
    except Exception:
        pass


def gerar_motor_oportunidades(top_n=100, margem_minima=20, apenas_oportunidade_positiva=True):
    try:
        base = globals().get("df", pd.DataFrame())
        if not isinstance(base, pd.DataFrame) or base.empty:
            base = globals().get("base_pesquisa", pd.DataFrame())
        if not isinstance(base, pd.DataFrame) or base.empty:
            return pd.DataFrame()

        base = base.copy()
        try:
            if "aplicar_filtro_empresa" in globals():
                base = aplicar_filtro_empresa(base)
        except Exception:
            pass

        empresa_id = empresa_contexto_atual() if "empresa_contexto_atual" in globals() else "1"
        empresa_nome = obter_nome_empresa(empresa_id) if "obter_nome_empresa" in globals() else ""

        col_ean = _oport_coluna(base, ["EAN", "EAN (GTIN)", "GTIN", "Código de Barras"])
        col_prod = _oport_coluna(base, ["Produto", "Produto_Base_SIM", "Descrição", "Descricao"])
        col_lab = _oport_coluna(base, ["Laboratório", "Laboratorio", "Fabricante", "Fornecedor"])
        col_cat = _oport_coluna(base, ["Categoria", "Família", "Familia", "Departamento", "Classe"])
        col_ganho = _oport_coluna(base, ["Ganho_Potencial", "Potencial de Captura", "Oportunidade", "Potencial"])
        col_fat = _oport_coluna(base, ["Faturamento", "Venda", "Receita", "Faturamento_Total"])
        col_margem = _oport_coluna(base, ["Margem_%", "Margem", "Margem %"])
        col_preco = _oport_coluna(base, ["Preco_Rede", "Preço Rede", "Preco_Venda", "Preço (R$)", "Preço"])
        col_custo = _oport_coluna(base, ["Custo", "Custo Médio", "Custo_Medio", "Custo Atual"])
        col_qtd = _oport_coluna(base, ["Quantidade", "Qtd", "Qtde", "Unidades", "Volume"])
        col_estoque = _oport_coluna(base, ["Estoque", "Estoque Atual", "Qtde Estoque"])
        col_conc = _oport_coluna(base, ["Menor_Preco_Concorrente", "Menor Concorrente", "Preco_Concorrente", "Preço Concorrente", "Menor_Preco"])

        trabalho = pd.DataFrame(index=base.index)
        trabalho["EmpresaID"] = empresa_id
        trabalho["Empresa"] = empresa_nome
        trabalho["EAN"] = base[col_ean].astype(str) if col_ean else ""
        trabalho["Produto"] = base[col_prod].astype(str) if col_prod else ""
        trabalho["Laboratório"] = base[col_lab].astype(str) if col_lab else "Não informado"
        trabalho["Categoria"] = base[col_cat].astype(str) if col_cat else "Não informado"

        if col_ganho:
            trabalho["Ganho_Potencial"] = _oport_converter_numero(base[col_ganho]).fillna(0)
        else:
            preco = _oport_converter_numero(base[col_preco]).fillna(0) if col_preco else pd.Series([0] * len(base), index=base.index)
            qtd = _oport_converter_numero(base[col_qtd]).fillna(1) if col_qtd else pd.Series([1] * len(base), index=base.index)
            margem = _oport_converter_numero(base[col_margem]).fillna(0) if col_margem else pd.Series([0] * len(base), index=base.index)
            fator = 0.03
            ajuste_margem = (float(margem_minima) - margem).clip(lower=0) / 100
            trabalho["Ganho_Potencial"] = (preco * qtd * (fator + ajuste_margem)).fillna(0)

        trabalho["Faturamento"] = _oport_converter_numero(base[col_fat]).fillna(0) if col_fat else 0
        trabalho["Margem_%"] = _oport_converter_numero(base[col_margem]).fillna(0) if col_margem else 0
        trabalho["Preço_Rede"] = _oport_converter_numero(base[col_preco]).fillna(0) if col_preco else 0
        trabalho["Custo"] = _oport_converter_numero(base[col_custo]).fillna(0) if col_custo else 0
        trabalho["Estoque"] = _oport_converter_numero(base[col_estoque]).fillna(0) if col_estoque else 0
        trabalho["Preço_Concorrente"] = _oport_converter_numero(base[col_conc]).fillna(0) if col_conc else 0

        def classificar(row):
            ganho = float(row.get("Ganho_Potencial", 0) or 0)
            margem = float(row.get("Margem_%", 0) or 0)
            estoque = float(row.get("Estoque", 0) or 0)
            preco = float(row.get("Preço_Rede", 0) or 0)
            conc = float(row.get("Preço_Concorrente", 0) or 0)
            if ganho > 0 and margem < float(margem_minima):
                return "Recuperar margem"
            if ganho > 0 and conc > 0 and preco > conc:
                return "Revisar competitividade"
            if ganho > 0 and estoque > 50:
                return "Giro de estoque"
            if ganho > 0:
                return "Ganho potencial"
            return "Monitorar"

        trabalho["Tipo_Oportunidade"] = trabalho.apply(classificar, axis=1)

        def acao(row):
            tipo = row.get("Tipo_Oportunidade", "")
            if tipo == "Recuperar margem":
                return "Avaliar preço, custo e negociação com fornecedor."
            if tipo == "Revisar competitividade":
                return "Simular ajuste de preço com base no concorrente."
            if tipo == "Giro de estoque":
                return "Avaliar ação comercial para acelerar giro."
            if tipo == "Ganho potencial":
                return "Priorizar análise no simulador inteligente."
            return "Manter acompanhamento."

        trabalho["Ação_Sugerida"] = trabalho.apply(acao, axis=1)

        agrup_cols = ["EmpresaID", "Empresa", "EAN", "Produto", "Laboratório", "Categoria"]
        trabalho = (
            trabalho.groupby(agrup_cols, dropna=False)
            .agg(
                Ganho_Potencial=("Ganho_Potencial", "sum"),
                Faturamento=("Faturamento", "sum"),
                Margem_Media=("Margem_%", "mean"),
                Estoque_Total=("Estoque", "sum"),
                Preco_Medio=("Preço_Rede", "mean"),
                Concorrente_Medio=("Preço_Concorrente", "mean"),
                Tipo_Oportunidade=("Tipo_Oportunidade", "first"),
                Ação_Sugerida=("Ação_Sugerida", "first")
            )
            .reset_index()
        )

        if apenas_oportunidade_positiva:
            trabalho = trabalho[trabalho["Ganho_Potencial"] > 0]

        trabalho = trabalho.sort_values("Ganho_Potencial", ascending=False).head(int(top_n))
        trabalho["Ranking"] = range(1, len(trabalho) + 1)

        cols = ["Ranking", "EmpresaID", "Empresa", "EAN", "Produto", "Laboratório", "Categoria", "Ganho_Potencial", "Faturamento", "Margem_Media", "Estoque_Total", "Preco_Medio", "Concorrente_Medio", "Tipo_Oportunidade", "Ação_Sugerida"]
        return trabalho[cols].copy()

    except Exception as erro:
        return pd.DataFrame([{
            "Ranking": 1, "EmpresaID": empresa_contexto_atual() if "empresa_contexto_atual" in globals() else "1",
            "Empresa": "", "EAN": "", "Produto": "", "Laboratório": "", "Categoria": "",
            "Ganho_Potencial": 0, "Faturamento": 0, "Margem_Media": 0, "Estoque_Total": 0,
            "Preco_Medio": 0, "Concorrente_Medio": 0, "Tipo_Oportunidade": "Erro", "Ação_Sugerida": str(erro)
        }])


def enviar_oportunidades_telegram(oportunidades_df, limite_envio=10):
    try:
        if oportunidades_df is None or oportunidades_df.empty:
            return False, "Nenhuma oportunidade para enviar."

        top = oportunidades_df.head(int(limite_envio))
        ganho_total = oportunidades_df["Ganho_Potencial"].sum() if "Ganho_Potencial" in oportunidades_df.columns else 0

        linhas = []
        for _, row in top.iterrows():
            linhas.append(f"• <b>{row.get('Produto', '')}</b> | R$ {_oport_numero_br(row.get('Ganho_Potencial', 0))}")

        mensagem = (
            "💰 <b>Motor de Oportunidades Eirox</b>\n\n"
            f"🏢 <b>Empresa:</b> {top.iloc[0].get('Empresa', '')}\n"
            f"🎯 <b>Oportunidades:</b> {len(oportunidades_df)}\n"
            f"💵 <b>Ganho potencial:</b> R$ {_oport_numero_br(ganho_total)}\n"
            f"🕒 <b>Horário:</b> {_oport_data_hora()}\n\n"
            + "\n".join(linhas)
            + f"\n\n🏷️ <b>Versão:</b> {VERSAO_APP}"
        )

        ok = enviar_alerta_telegram(mensagem) if "enviar_alerta_telegram" in globals() else False
        return bool(ok), "Oportunidades enviadas ao Telegram." if ok else "Não foi possível enviar ao Telegram."
    except Exception as erro:
        return False, str(erro)


def usuario_pode_ver_motor_oportunidades():
    try:
        return usuario_master() or tela_liberada_por_plano("💰 Motor de Oportunidades")
    except Exception:
        return False

# --------------------------------------------------
# RELEASE CANDIDATE CENTER - v1.36.3 RC
# --------------------------------------------------

ARQUIVOS_ADMINISTRATIVOS_RC = [
    "USUARIOS_EIROX.csv",
    "EMPRESAS_EIROX.csv",
    "LICENCAS_EIROX.csv",
    "ALERTAS_EIROX.csv",
    "OPORTUNIDADES_EIROX.csv",
    "logs/log_acessos.csv",
    "logs/log_usuarios.csv"
]


def usuario_pode_ver_release_candidate():
    try:
        return usuario_master() if "usuario_master" in globals() else str(st.session_state.get("usuario", "")).lower() == "paulomarques"
    except Exception:
        return False


def _rc_tamanho_formatado(bytes_valor):
    try:
        bytes_valor = float(bytes_valor)
        if bytes_valor >= 1024 ** 3:
            return f"{bytes_valor / (1024 ** 3):.2f} GB".replace(".", ",")
        if bytes_valor >= 1024 ** 2:
            return f"{bytes_valor / (1024 ** 2):.2f} MB".replace(".", ",")
        if bytes_valor >= 1024:
            return f"{bytes_valor / 1024:.2f} KB".replace(".", ",")
        return f"{int(bytes_valor)} B"
    except Exception:
        return "0 B"


def status_arquivo_rc(caminho):
    try:
        p = Path(caminho)
        if not p.exists():
            return {"Arquivo": caminho, "Status": "🟡 Não encontrado", "Tamanho": "0 B", "Última Atualização": "-"}
        return {
            "Arquivo": caminho,
            "Status": "🟢 OK",
            "Tamanho": _rc_tamanho_formatado(p.stat().st_size),
            "Última Atualização": datetime.fromtimestamp(p.stat().st_mtime).strftime("%d/%m/%Y %H:%M:%S")
        }
    except Exception as erro:
        return {"Arquivo": caminho, "Status": "🔴 Erro", "Tamanho": "0 B", "Última Atualização": str(erro)}


def gerar_checklist_rc():
    checks = []

    def add(item, status, detalhe):
        checks.append({"Item": item, "Status": status, "Detalhe": detalhe})

    try:
        add("Versão RC", "🟢 OK" if "rc" in VERSAO_APP.lower() else "🟡 Atenção", VERSAO_APP)
        add("Controle de Usuários", "🟢 OK" if "carregar_usuarios_sistema" in globals() else "🔴 Erro", "Cadastro, bloqueio, reset e expiração")
        add("Multiempresa", "🟢 OK" if "carregar_empresas_sistema" in globals() else "🔴 Erro", "Empresas e contexto master")
        add("Licenciamento Real", "🟢 OK" if "carregar_licencas_sistema" in globals() else "🔴 Erro", "Planos, limites e expiração")
        add("Auditoria", "🟢 OK" if "carregar_logs_acesso" in globals() else "🔴 Erro", "Histórico de acesso e navegação")
        add("Saúde do Sistema", "🟢 OK" if "gerar_saude_bases" in globals() else "🔴 Erro", "Monitoramento das bases")
        add("Backup Center", "🟢 OK" if "gerar_backup_eirox" in globals() else "🔴 Erro", "Backup e download")
        add("Alertas Inteligentes", "🟢 OK" if "gerar_alertas_inteligentes" in globals() else "🔴 Erro", "Alertas e Telegram")
        add("Motor de Oportunidades", "🟢 OK" if "gerar_motor_oportunidades" in globals() else "🔴 Erro", "Ranking financeiro")
        add("Telegram", health_status_telegram() if "health_status_telegram" in globals() else "🟡 Não verificado", "Integração de notificações")
        try:
            emp = empresa_contexto_atual() if "empresa_contexto_atual" in globals() else "1"
            lic = status_licenca_empresa(emp) if "status_licenca_empresa" in globals() else {}
            add("Licença empresa contexto", lic.get("StatusOperacional", "🟡 Não verificado"), lic.get("Mensagem", ""))
        except Exception:
            add("Licença empresa contexto", "🟡 Não verificado", "")
    except Exception as erro:
        add("Checklist RC", "🔴 Erro", str(erro))

    return pd.DataFrame(checks)


def gerar_status_arquivos_rc():
    return pd.DataFrame([status_arquivo_rc(c) for c in ARQUIVOS_ADMINISTRATIVOS_RC])


def gerar_resumo_release_candidate():
    try:
        checklist = gerar_checklist_rc()
        arquivos = gerar_status_arquivos_rc()
        total_checks = len(checklist)
        ok_checks = int(checklist["Status"].astype(str).str.contains("OK|Ativa|Trial|Protegido|Configurado", regex=True, na=False).sum()) if not checklist.empty else 0
        arquivos_ok = int(arquivos["Status"].astype(str).str.contains("OK", na=False).sum()) if not arquivos.empty else 0
        status_final = "🟢 RC pronta para homologação final" if ok_checks >= max(total_checks - 2, 1) else "🟡 RC com pendências"
        return {"Status": status_final, "ChecksOK": ok_checks, "TotalChecks": total_checks, "ArquivosOK": arquivos_ok, "TotalArquivos": len(arquivos)}
    except Exception:
        return {"Status": "🔴 Erro no resumo RC", "ChecksOK": 0, "TotalChecks": 0, "ArquivosOK": 0, "TotalArquivos": 0}




# --------------------------------------------------
# IA PRICING ENTERPRISE - v1.37.0
# --------------------------------------------------

IA_PRICING_ARQUIVO = Path("IA_PRICING_EIROX.csv")


def usuario_pode_ver_ia_pricing():
    try:
        return usuario_master() or tela_liberada_por_plano("🤖 IA Pricing Enterprise")
    except Exception:
        return False


def _ia_numero_br(valor, casas=2):
    try:
        return f"{float(valor):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00"


def _ia_coluna(base, possibilidades):
    try:
        cols = list(base.columns)
        for alvo in possibilidades:
            alvo_norm = str(alvo).strip().lower()
            for c in cols:
                if str(c).strip().lower() == alvo_norm:
                    return c
        for alvo in possibilidades:
            alvo_norm = str(alvo).strip().lower()
            for c in cols:
                if alvo_norm in str(c).strip().lower():
                    return c
    except Exception:
        pass
    return None


def _ia_num(serie):
    try:
        if "converter_numero_brasil" in globals():
            return converter_numero_brasil(serie)
        return pd.to_numeric(serie.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False), errors="coerce")
    except Exception:
        return pd.to_numeric(serie, errors="coerce")


def carregar_historico_ia_pricing():
    try:
        if not IA_PRICING_ARQUIVO.exists():
            return pd.DataFrame()
        return pd.read_csv(IA_PRICING_ARQUIVO, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
    except Exception:
        return pd.DataFrame()


def salvar_recomendacoes_ia(ia_df):
    try:
        if ia_df is None or ia_df.empty:
            return
        out = ia_df.copy()
        out["Data_Hora"] = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S") if "ZoneInfo" in globals() else datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        if IA_PRICING_ARQUIVO.exists():
            old = pd.read_csv(IA_PRICING_ARQUIVO, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
            out = pd.concat([old, out], ignore_index=True)
        out.to_csv(IA_PRICING_ARQUIVO, index=False, sep=";", encoding="utf-8-sig")
    except Exception:
        pass


def gerar_ia_pricing_enterprise(margem_minima=25, margem_alvo=35, limite_reducao=8, limite_aumento=12, top_n=150):
    try:
        base = globals().get("df", pd.DataFrame())
        if not isinstance(base, pd.DataFrame) or base.empty:
            base = globals().get("base_pesquisa", pd.DataFrame())
        if not isinstance(base, pd.DataFrame) or base.empty:
            return pd.DataFrame()
        base = base.copy()
        try:
            if "aplicar_filtro_empresa" in globals():
                base = aplicar_filtro_empresa(base)
        except Exception:
            pass
        empresa_id = empresa_contexto_atual() if "empresa_contexto_atual" in globals() else "1"
        empresa_nome = obter_nome_empresa(empresa_id) if "obter_nome_empresa" in globals() else ""
        col_ean = _ia_coluna(base, ["EAN", "EAN (GTIN)", "GTIN", "Código de Barras"])
        col_prod = _ia_coluna(base, ["Produto", "Produto_Base_SIM", "Descrição", "Descricao"])
        col_lab = _ia_coluna(base, ["Laboratório", "Laboratorio", "Fabricante", "Fornecedor"])
        col_cat = _ia_coluna(base, ["Categoria", "Família", "Familia", "Departamento", "Classe"])
        col_curva = _ia_coluna(base, ["CURVA", "Curva", "ABC", "Curva ABC"])
        col_preco = _ia_coluna(base, ["Preco_Rede", "Preço Rede", "Preco_Venda", "Preço (R$)", "Preço", "Preco"])
        col_custo = _ia_coluna(base, ["Custo", "Custo Médio", "Custo_Medio", "Custo Atual"])
        col_margem = _ia_coluna(base, ["Margem_%", "Margem", "Margem %"])
        col_conc = _ia_coluna(base, ["Menor_Preco_Concorrente", "Menor Concorrente", "Preco_Concorrente", "Preço Concorrente", "Menor_Preco"])
        col_ganho = _ia_coluna(base, ["Ganho_Potencial", "Potencial de Captura", "Oportunidade", "Potencial"])
        col_estoque = _ia_coluna(base, ["Estoque", "Estoque Atual", "Qtde Estoque"])
        col_qtd = _ia_coluna(base, ["Quantidade", "Qtd", "Qtde", "Unidades", "Volume"])
        n=len(base)
        idx=base.index
        preco = _ia_num(base[col_preco]).fillna(0) if col_preco else pd.Series([0]*n,index=idx)
        custo = _ia_num(base[col_custo]).fillna(0) if col_custo else pd.Series([0]*n,index=idx)
        margem = _ia_num(base[col_margem]).fillna(0) if col_margem else pd.Series([0]*n,index=idx)
        conc = _ia_num(base[col_conc]).fillna(0) if col_conc else pd.Series([0]*n,index=idx)
        ganho = _ia_num(base[col_ganho]).fillna(0) if col_ganho else pd.Series([0]*n,index=idx)
        estoque = _ia_num(base[col_estoque]).fillna(0) if col_estoque else pd.Series([0]*n,index=idx)
        qtd = _ia_num(base[col_qtd]).fillna(1) if col_qtd else pd.Series([1]*n,index=idx)
        margem_calc=margem.copy()
        mask=(margem_calc<=0)&(preco>0)&(custo>0)
        margem_calc.loc[mask]=((preco.loc[mask]-custo.loc[mask])/preco.loc[mask])*100
        preco_rec=preco.copy()
        preco_alvo = custo / max((1-float(margem_alvo)/100),0.01)
        mask_subir=(preco>0)&(custo>0)&(margem_calc<float(margem_minima))&(preco_alvo>preco)
        preco_rec.loc[mask_subir]=preco_alvo.loc[mask_subir]
        dif=pd.Series([0]*n,index=idx,dtype='float')
        mask_conc=(preco>0)&(conc>0)
        dif.loc[mask_conc]=((preco.loc[mask_conc]-conc.loc[mask_conc])/preco.loc[mask_conc])*100
        mask_red=(dif>float(limite_reducao))&(margem_calc>=float(margem_minima))
        preco_rec.loc[mask_red]=preco.loc[mask_red]*(1-float(limite_reducao)/100)
        max_aum=preco*(1+float(limite_aumento)/100)
        mask_lim=(preco>0)&(preco_rec>max_aum)
        preco_rec.loc[mask_lim]=max_aum.loc[mask_lim]
        var=pd.Series([0]*n,index=idx,dtype='float')
        mask_preco=preco>0
        var.loc[mask_preco]=((preco_rec.loc[mask_preco]-preco.loc[mask_preco])/preco.loc[mask_preco])*100
        margem_rec=pd.Series([0]*n,index=idx,dtype='float')
        mask_pr=preco_rec>0
        margem_rec.loc[mask_pr]=((preco_rec.loc[mask_pr]-custo.loc[mask_pr])/preco_rec.loc[mask_pr])*100
        ganho_est=((preco_rec-preco)*qtd).fillna(0)
        ganho_est=ganho_est.where(ganho_est.abs()>0, ganho)
        out=pd.DataFrame(index=idx)
        out["EmpresaID"]=empresa_id; out["Empresa"]=empresa_nome
        out["EAN"]=base[col_ean].astype(str) if col_ean else ""
        out["Produto"]=base[col_prod].astype(str) if col_prod else ""
        out["Laboratório"]=base[col_lab].astype(str) if col_lab else "Não informado"
        out["Categoria"]=base[col_cat].astype(str) if col_cat else "Não informado"
        out["Curva"]=base[col_curva].astype(str) if col_curva else "Não informado"
        out["Preço_Atual"]=preco; out["Preço_Recomendado"]=preco_rec; out["Variação_Pct"]=var
        out["Margem_Atual"]=margem_calc; out["Margem_Recomendada"]=margem_rec; out["Preço_Concorrente"]=conc
        out["Estoque"]=estoque; out["Ganho_Estimado"]=ganho_est
        def acao(row):
            v=float(row.get("Variação_Pct",0) or 0); m=float(row.get("Margem_Atual",0) or 0); c=float(row.get("Preço_Concorrente",0) or 0); p=float(row.get("Preço_Atual",0) or 0); e=float(row.get("Estoque",0) or 0)
            if v>1: return "Aumentar preço"
            if v<-1: return "Reduzir preço"
            if m<float(margem_minima): return "Revisar margem"
            if c>0 and p>c: return "Monitorar concorrência"
            if e>50: return "Avaliar giro"
            return "Manter"
        out["Ação"]=out.apply(acao,axis=1)
        out["Motivo"]=out["Ação"].map({
            "Aumentar preço":"Margem abaixo da meta ou oportunidade de recuperação de rentabilidade.",
            "Reduzir preço":"Concorrência mais agressiva com margem suficiente para ajuste controlado.",
            "Revisar margem":"Margem abaixo do limite mínimo configurado.",
            "Monitorar concorrência":"Preço atual acima do concorrente identificado.",
            "Avaliar giro":"Estoque elevado exige acompanhamento comercial.",
            "Manter":"Preço dentro dos parâmetros configurados."
        }).fillna("Analisar produto.")
        out["Score_IA"]=(out["Ganho_Estimado"].abs().rank(pct=True).fillna(0)*40+(100-out["Margem_Atual"].clip(0,100))*0.25+out["Variação_Pct"].abs().clip(upper=50)*0.7+out["Estoque"].rank(pct=True).fillna(0)*10).round(2)
        cols_group=["EmpresaID","Empresa","EAN","Produto","Laboratório","Categoria","Curva","Ação","Motivo"]
        agg=out.groupby(cols_group,dropna=False).agg(Score_IA=("Score_IA","max"),Preço_Atual=("Preço_Atual","mean"),Preço_Recomendado=("Preço_Recomendado","mean"),Variação_Pct=("Variação_Pct","mean"),Margem_Atual=("Margem_Atual","mean"),Margem_Recomendada=("Margem_Recomendada","mean"),Preço_Concorrente=("Preço_Concorrente","mean"),Estoque=("Estoque","sum"),Ganho_Estimado=("Ganho_Estimado","sum")).reset_index()
        agg=agg.sort_values(["Score_IA","Ganho_Estimado"],ascending=False).head(int(top_n))
        agg["Ranking"]=range(1,len(agg)+1)
        return agg[["Ranking","EmpresaID","Empresa","EAN","Produto","Laboratório","Categoria","Curva","Ação","Preço_Atual","Preço_Recomendado","Variação_Pct","Margem_Atual","Margem_Recomendada","Preço_Concorrente","Estoque","Ganho_Estimado","Score_IA","Motivo"]]
    except Exception as erro:
        return pd.DataFrame([{"Ranking":1,"EmpresaID":"1","Empresa":"","EAN":"","Produto":"","Laboratório":"","Categoria":"","Curva":"","Ação":"Erro","Preço_Atual":0,"Preço_Recomendado":0,"Variação_Pct":0,"Margem_Atual":0,"Margem_Recomendada":0,"Preço_Concorrente":0,"Estoque":0,"Ganho_Estimado":0,"Score_IA":0,"Motivo":str(erro)}])


def enviar_ia_pricing_telegram(ia_df, limite_envio=10):
    try:
        if ia_df is None or ia_df.empty:
            return False, "Nenhuma recomendação para enviar."
        top=ia_df.head(int(limite_envio)); ganho_total=ia_df["Ganho_Estimado"].sum() if "Ganho_Estimado" in ia_df.columns else 0
        linhas=[f"• <b>{r.get('Produto','')}</b> | {r.get('Ação','')} | R$ {_ia_numero_br(r.get('Preço_Recomendado',0))}" for _,r in top.iterrows()]
        mensagem=("🤖 <b>IA Pricing Enterprise</b>\n\n"+f"🏢 <b>Empresa:</b> {top.iloc[0].get('Empresa','')}\n"+f"🎯 <b>Recomendações:</b> {len(ia_df)}\n"+f"💵 <b>Ganho estimado:</b> R$ {_ia_numero_br(ganho_total)}\n\n"+"\n".join(linhas)+f"\n\n🏷️ <b>Versão:</b> {VERSAO_APP}")
        ok=enviar_alerta_telegram(mensagem) if "enviar_alerta_telegram" in globals() else False
        return bool(ok), "Recomendações enviadas ao Telegram." if ok else "Não foi possível enviar ao Telegram."
    except Exception as erro:
        return False, str(erro)



# --------------------------------------------------
# WORKFLOW COMERCIAL - v1.37.1
# --------------------------------------------------

WORKFLOW_COMERCIAL_ARQUIVO = Path("WORKFLOW_COMERCIAL_EIROX.csv")


def usuario_pode_ver_workflow_comercial():
    try:
        return usuario_master() or tela_liberada_por_plano("📋 Workflow Comercial")
    except Exception:
        return False


def _wf_data_hora():
    try:
        return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def carregar_workflow_comercial():
    try:
        if not WORKFLOW_COMERCIAL_ARQUIVO.exists():
            return pd.DataFrame(columns=[
                "ID", "Data_Hora", "EmpresaID", "Empresa", "Usuario", "EAN", "Produto",
                "Acao_IA", "Preco_Atual", "Preco_Recomendado", "Ganho_Estimado",
                "Status", "Justificativa", "Origem", "Versao"
            ])

        return pd.read_csv(
            WORKFLOW_COMERCIAL_ARQUIVO,
            sep=";",
            encoding="utf-8-sig",
            dtype=str
        ).fillna("")

    except Exception:
        return pd.DataFrame()


def salvar_workflow_comercial(base):
    try:
        base.to_csv(
            WORKFLOW_COMERCIAL_ARQUIVO,
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )
        return True
    except Exception:
        return False


def adicionar_recomendacoes_ao_workflow(recomendacoes_df, origem="IA Pricing"):
    try:
        if recomendacoes_df is None or recomendacoes_df.empty:
            return False, "Nenhuma recomendação disponível."

        workflow = carregar_workflow_comercial()
        novos = []

        for _, row in recomendacoes_df.iterrows():
            empresa_id = str(row.get("EmpresaID", empresa_contexto_atual() if "empresa_contexto_atual" in globals() else "1"))
            empresa = str(row.get("Empresa", obter_nome_empresa(empresa_id) if "obter_nome_empresa" in globals() else ""))
            ean = str(row.get("EAN", ""))
            produto = str(row.get("Produto", ""))
            acao = str(row.get("Ação", row.get("Tipo_Oportunidade", "")))
            preco_atual = str(row.get("Preço_Atual", row.get("Preco_Medio", "")))
            preco_rec = str(row.get("Preço_Recomendado", row.get("Preco_Recomendado", "")))
            ganho = str(row.get("Ganho_Estimado", row.get("Ganho_Potencial", "")))

            if not workflow.empty and all(c in workflow.columns for c in ["EAN", "Produto", "EmpresaID", "Status"]):
                pendente = workflow[
                    (workflow["EAN"].astype(str) == ean) &
                    (workflow["Produto"].astype(str) == produto) &
                    (workflow["EmpresaID"].astype(str) == empresa_id) &
                    (workflow["Status"].astype(str).isin(["Pendente", "Em análise"]))
                ]
                if not pendente.empty:
                    continue

            novos.append({
                "ID": f"WF-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(novos)+1}",
                "Data_Hora": _wf_data_hora(),
                "EmpresaID": empresa_id,
                "Empresa": empresa,
                "Usuario": st.session_state.get("usuario", ""),
                "EAN": ean,
                "Produto": produto,
                "Acao_IA": acao,
                "Preco_Atual": preco_atual,
                "Preco_Recomendado": preco_rec,
                "Ganho_Estimado": ganho,
                "Status": "Pendente",
                "Justificativa": "",
                "Origem": origem,
                "Versao": VERSAO_APP
            })

        if not novos:
            return False, "Nenhuma nova recomendação foi adicionada. Pode já existir pendência para esses itens."

        final = pd.concat([workflow, pd.DataFrame(novos)], ignore_index=True)
        salvar_workflow_comercial(final)

        try:
            enviar_alerta_telegram(
                "📋 <b>Workflow Comercial atualizado</b>\\n\\n"
                f"✅ <b>Novas recomendações:</b> {len(novos)}\\n"
                f"👤 <b>Usuário:</b> {st.session_state.get('usuario', '')}\\n"
                f"🕒 <b>Horário:</b> {_wf_data_hora()}\\n"
                f"🏷️ <b>Versão:</b> {VERSAO_APP}"
            )
        except Exception:
            pass

        return True, f"{len(novos)} recomendações enviadas para aprovação."

    except Exception as erro:
        return False, f"Erro ao adicionar ao workflow: {erro}"


def atualizar_status_workflow(ids, novo_status, justificativa):
    try:
        if not ids:
            return False, "Selecione ao menos uma recomendação."

        if novo_status in ["Aprovado", "Rejeitado"] and not str(justificativa).strip():
            return False, "Justificativa obrigatória para aprovar ou rejeitar."

        base = carregar_workflow_comercial()

        if base.empty:
            return False, "Workflow vazio."

        ids = [str(i) for i in ids]
        mask = base["ID"].astype(str).isin(ids)

        if not mask.any():
            return False, "Nenhum ID encontrado."

        base.loc[mask, "Status"] = novo_status
        base.loc[mask, "Justificativa"] = str(justificativa).strip()
        base.loc[mask, "Usuario"] = st.session_state.get("usuario", "")
        base.loc[mask, "Data_Hora"] = _wf_data_hora()
        base.loc[mask, "Versao"] = VERSAO_APP

        salvar_workflow_comercial(base)

        try:
            enviar_alerta_telegram(
                "📋 <b>Status do Workflow Comercial alterado</b>\\n\\n"
                f"🔁 <b>Status:</b> {novo_status}\\n"
                f"📦 <b>Itens:</b> {len(ids)}\\n"
                f"👤 <b>Usuário:</b> {st.session_state.get('usuario', '')}\\n"
                f"🕒 <b>Horário:</b> {_wf_data_hora()}\\n"
                f"📝 <b>Justificativa:</b> {str(justificativa).strip()[:300]}"
            )
        except Exception:
            pass

        return True, f"{len(ids)} recomendações atualizadas para {novo_status}."

    except Exception as erro:
        return False, f"Erro ao atualizar workflow: {erro}"




# --------------------------------------------------
# CRM ENTERPRISE / GESTÃO DE CLIENTES - v1.38.0
# --------------------------------------------------

CLIENTES_EIROX_ARQUIVO = Path("CLIENTES_EIROX.csv")


def usuario_pode_ver_crm_enterprise():
    try:
        return usuario_master() if "usuario_master" in globals() else str(st.session_state.get("usuario", "")).lower() in ["paulomarques"]
    except Exception:
        return False


def _crm_data_hora():
    try:
        return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def _crm_numero_br(valor, casas=2):
    try:
        return f"{float(valor):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00"


def inicializar_clientes_eirox():
    try:
        if not CLIENTES_EIROX_ARQUIVO.exists():
            base = pd.DataFrame(
                [
                    {
                        "ClienteID": "1",
                        "EmpresaID": "1",
                        "Cliente": "Marabá - Cliente teste",
                        "CNPJ": "",
                        "Cidade": "Marabá",
                        "UF": "PA",
                        "Qtd_Lojas": "0",
                        "Plano": "Enterprise",
                        "MRR": "0",
                        "Data_Implantacao": "",
                        "Data_Renovacao": "",
                        "Status": "Implantação",
                        "Responsavel_Comercial": "",
                        "Observacao": "Cliente teste criado automaticamente",
                        "Criado_Em": _crm_data_hora()
                    },
                    {
                        "ClienteID": "2",
                        "EmpresaID": "2",
                        "Cliente": "Belém - Cliente teste",
                        "CNPJ": "",
                        "Cidade": "Belém",
                        "UF": "PA",
                        "Qtd_Lojas": "0",
                        "Plano": "Starter",
                        "MRR": "0",
                        "Data_Implantacao": "",
                        "Data_Renovacao": "",
                        "Status": "Implantação",
                        "Responsavel_Comercial": "",
                        "Observacao": "Cliente teste criado automaticamente",
                        "Criado_Em": _crm_data_hora()
                    }
                ]
            )

            base.to_csv(
                CLIENTES_EIROX_ARQUIVO,
                index=False,
                sep=";",
                encoding="utf-8-sig"
            )

        return True
    except Exception:
        return False


@st.cache_data(ttl=60, show_spinner=False)
def carregar_clientes_eirox():
    try:
        inicializar_clientes_eirox()

        base = pd.read_csv(
            CLIENTES_EIROX_ARQUIVO,
            sep=";",
            encoding="utf-8-sig",
            dtype=str
        ).fillna("")

        obrigatorias = [
            "ClienteID",
            "EmpresaID",
            "Cliente",
            "CNPJ",
            "Cidade",
            "UF",
            "Qtd_Lojas",
            "Plano",
            "MRR",
            "Data_Implantacao",
            "Data_Renovacao",
            "Status",
            "Responsavel_Comercial",
            "Observacao",
            "Criado_Em"
        ]

        for col in obrigatorias:
            if col not in base.columns:
                base[col] = ""

        return base[obrigatorias].copy()

    except Exception:
        return pd.DataFrame()


def salvar_clientes_eirox(base):
    try:
        base = base.copy()

        base.to_csv(
            CLIENTES_EIROX_ARQUIVO,
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        try:
            carregar_clientes_eirox.clear()
        except Exception:
            pass

        return True

    except Exception:
        return False


def criar_ou_atualizar_cliente_eirox(
    cliente_id,
    empresa_id,
    cliente,
    cnpj,
    cidade,
    uf,
    qtd_lojas,
    plano,
    mrr,
    data_implantacao,
    data_renovacao,
    status,
    responsavel,
    observacao
):
    try:
        cliente_id = str(cliente_id).strip()
        empresa_id = str(empresa_id).strip()
        cliente = str(cliente).strip()

        if not cliente_id or not empresa_id or not cliente:
            return False, "ClienteID, EmpresaID e Cliente são obrigatórios."

        base = carregar_clientes_eirox()

        nova_linha = {
            "ClienteID": cliente_id,
            "EmpresaID": empresa_id,
            "Cliente": cliente,
            "CNPJ": str(cnpj).strip(),
            "Cidade": str(cidade).strip(),
            "UF": str(uf).strip().upper(),
            "Qtd_Lojas": str(qtd_lojas).strip(),
            "Plano": str(plano).strip(),
            "MRR": str(mrr).strip(),
            "Data_Implantacao": str(data_implantacao).strip(),
            "Data_Renovacao": str(data_renovacao).strip(),
            "Status": str(status).strip(),
            "Responsavel_Comercial": str(responsavel).strip(),
            "Observacao": str(observacao).strip(),
            "Criado_Em": _crm_data_hora()
        }

        if not base.empty and cliente_id in base["ClienteID"].astype(str).tolist():
            idx = base.index[base["ClienteID"].astype(str) == cliente_id][0]
            for k, v in nova_linha.items():
                if k != "Criado_Em":
                    base.loc[idx, k] = v
            acao = "Atualização de cliente"
        else:
            base = pd.concat([base, pd.DataFrame([nova_linha])], ignore_index=True)
            acao = "Criação de cliente"

        salvar_clientes_eirox(base)

        try:
            registrar_log_usuario(
                acao,
                cliente,
                f"EmpresaID={empresa_id} | Plano={plano} | Status={status}"
            )
        except Exception:
            pass

        try:
            enviar_alerta_telegram(
                "🏢 <b>Cliente CRM Eirox atualizado</b>\\n\\n"
                f"🏪 <b>Cliente:</b> {cliente}\\n"
                f"📦 <b>Plano:</b> {plano}\\n"
                f"🔐 <b>Status:</b> {status}\\n"
                f"💰 <b>MRR:</b> R$ {_crm_numero_br(str(mrr).replace(',', '.'))}\\n"
                f"👤 <b>Usuário:</b> {st.session_state.get('usuario', '')}\\n"
                f"🕒 <b>Horário:</b> {_crm_data_hora()}\\n"
                f"🏷️ <b>Versão:</b> {VERSAO_APP}"
            )
        except Exception:
            pass

        return True, f"{acao} realizada com sucesso."

    except Exception as erro:
        return False, f"Erro ao salvar cliente: {erro}"


def metricas_crm_enterprise():
    try:
        base = carregar_clientes_eirox()

        if base.empty:
            return {
                "Clientes": 0,
                "Ativos": 0,
                "Implantacao": 0,
                "Suspensos": 0,
                "Lojas": 0,
                "MRR": 0
            }

        mrr = pd.to_numeric(
            base["MRR"].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
            errors="coerce"
        ).fillna(0)

        lojas = pd.to_numeric(base["Qtd_Lojas"], errors="coerce").fillna(0)

        return {
            "Clientes": int(len(base)),
            "Ativos": int((base["Status"].astype(str).str.lower() == "ativo").sum()),
            "Implantacao": int((base["Status"].astype(str).str.lower() == "implantação").sum() + (base["Status"].astype(str).str.lower() == "implantacao").sum()),
            "Suspensos": int((base["Status"].astype(str).str.lower() == "suspenso").sum()),
            "Lojas": int(lojas.sum()),
            "MRR": float(mrr.sum())
        }

    except Exception:
        return {
            "Clientes": 0,
            "Ativos": 0,
            "Implantacao": 0,
            "Suspensos": 0,
            "Lojas": 0,
            "MRR": 0
        }




# --------------------------------------------------
# MENU POR PLANO - v1.38.1
# --------------------------------------------------

TELAS_CLIENTE_POR_PLANO = {
    "Starter": [
        "🏢 Portal do Cliente",
        "🎯 Sugestão de Pesquisa",
        "🏢 Dashboard Executivo",
        "🔎 Rede/Loja vs Concorrentes",
    ],
    "Professional": [
        "🏢 Portal do Cliente",
        "💰 Motor de Oportunidades",
        "🚨 Alertas Inteligentes",
        "🎯 Sugestão de Pesquisa",
        "📈 Simulador Inteligente",
        "🏢 Dashboard Executivo",
        "🌎 Mapa Geográfico de Concorrência",
        "🔎 Rede/Loja vs Concorrentes",
        "🛒 Negociação Compras",
        "🚨 Central de Alertas",
    ],
    "Enterprise": [
        "🏢 Portal do Cliente",
        "📋 Workflow Comercial",
        "🤖 IA Pricing Enterprise",
        "💰 Motor de Oportunidades",
        "🚨 Alertas Inteligentes",
        "🎯 Sugestão de Pesquisa",
        "📈 Simulador Inteligente",
        "🏢 Dashboard Executivo",
        "🌎 Mapa Geográfico de Concorrência",
        "🔎 Rede/Loja vs Concorrentes",
        "🛒 Negociação Compras",
        "🚨 Central de Alertas",
    ],
    "Enterprise Plus": [
        "🏢 Portal do Cliente",
        "📋 Workflow Comercial",
        "🤖 IA Pricing Enterprise",
        "💰 Motor de Oportunidades",
        "🚨 Alertas Inteligentes",
        "🎯 Sugestão de Pesquisa",
        "📈 Simulador Inteligente",
        "🏢 Dashboard Executivo",
        "🌎 Mapa Geográfico de Concorrência",
        "🔎 Rede/Loja vs Concorrentes",
        "🛒 Negociação Compras",
        "🚨 Central de Alertas",
    ]
}

TELAS_ADMIN_EIROX = [
    "👥 Controle de Usuários",
    "🔐 Central de Auditoria",
    "📋 Central de Auditoria",
    "🟢 Saúde do Sistema",
    "📦 Backup Center",
    "🏢 Multiempresa",
    "💼 Licenciamento Multiempresa",
    "💼 Licenciamento Real",
    "🏢 CRM Enterprise",
    "🏁 Release Candidate",
    "📌 Sobre o Eirox",
    "🧭 Roadmap do Produto",
    "🧪 Diagnóstico",
    "💳 Billing Enterprise"]


def plano_empresa_contexto():
    try:
        empresa_id = empresa_contexto_atual() if "empresa_contexto_atual" in globals() else st.session_state.get("empresa_id_usuario", "1")
        lic = obter_licenca_empresa(empresa_id) if "obter_licenca_empresa" in globals() else None
        if lic:
            return str(lic.get("Plano", "Starter")).strip() or "Starter"
        return "Starter"
    except Exception:
        return "Starter"


def tela_liberada_por_plano(pagina_nome):
    try:
        if usuario_master():
            return True

        plano = plano_empresa_contexto()
        telas = TELAS_CLIENTE_POR_PLANO.get(plano, TELAS_CLIENTE_POR_PLANO["Starter"])

        pagina_txt = str(pagina_nome).strip()
        pagina_norm = pagina_txt.lower()

        if pagina_txt in telas:
            return True

        # Compatibilidade por palavras-chave para evitar sumiço de módulos por pequenas mudanças no nome da tela.
        grupos = {
            "dashboard": ["dashboard", "painel"],
            "rede": ["rede/loja", "concorrente"],
            "sugestao": ["sugestão", "sugestao", "pesquisa"],
            "simulador": ["simulador"],
            "mapa": ["mapa", "geográfico", "geografico"],
            "alertas": ["alerta"],
            "motor": ["motor", "oportunidade"],
            "ia": ["ia pricing", "pricing enterprise"],
            "workflow": ["workflow"],
            "negociacao": ["negociação", "negociacao", "compras"],
            "portal": ["portal do cliente"]
        }

        def grupo_da_pagina(nome):
            nome = str(nome).lower()
            for grupo, palavras in grupos.items():
                if any(p in nome for p in palavras):
                    return grupo
            return None

        grupo_pagina = grupo_da_pagina(pagina_norm)

        if not grupo_pagina:
            return False

        grupos_liberados = set()

        for tela in telas:
            g = grupo_da_pagina(tela)
            if g:
                grupos_liberados.add(g)

        return grupo_pagina in grupos_liberados

    except Exception:
        return False


def filtrar_paginas_por_plano(paginas):
    try:
        paginas = list(paginas)

        if usuario_master():
            return paginas

        plano = plano_empresa_contexto()

        admin_pages = ['🏁 Release Candidate', '🏢 CRM Enterprise', '🏢 Multiempresa', '👥 Controle de Usuários', '💳 Billing Enterprise', '💼 Licenciamento Multiempresa', '💼 Licenciamento Real', '📌 Sobre o Eirox', '📦 Backup Center', '🔐 Central de Auditoria', '🟢 Saúde do Sistema', '🧪 Diagnóstico', '🧭 Roadmap do Produto']

        # Garante que todas as páginas de cliente existentes entrem no menu conforme o plano.
        todas_paginas_cliente = ['🏢 Portal do Cliente', '📋 Workflow Comercial', '🤖 IA Pricing Enterprise', '💰 Motor de Oportunidades', '🚨 Alertas Inteligentes', '🎯 Sugestão de Pesquisa', '📈 Simulador Inteligente', '🏢 Dashboard Executivo', '🌎 Mapa Geográfico de Concorrência', '🔎 Rede/Loja vs Concorrentes', '🛒 Negociação Compras', '🚨 Central de Alertas']

        for p in todas_paginas_cliente:
            if p not in paginas:
                paginas.append(p)

        telas_liberadas = TELAS_CLIENTE_POR_PLANO.get(plano, TELAS_CLIENTE_POR_PLANO["Starter"])

        liberadas = []

        for p in paginas:
            if p in admin_pages:
                continue

            if p in telas_liberadas:
                liberadas.append(p)

        return liberadas

    except Exception:
        return paginas


def dividir_menu_cliente_admin(paginas):
    """
    Separa menu em Área do Cliente e Administração Eirox.
    """

    try:
        paginas = list(paginas)

        admin_pages = ['🏁 Release Candidate', '🏢 CRM Enterprise', '🏢 Multiempresa', '👥 Controle de Usuários', '💳 Billing Enterprise', '💼 Licenciamento Multiempresa', '💼 Licenciamento Real', '📌 Sobre o Eirox', '📦 Backup Center', '🔐 Central de Auditoria', '🟢 Saúde do Sistema', '🧪 Diagnóstico', '🧭 Roadmap do Produto']

        cliente = [p for p in paginas if p not in admin_pages]
        admin = [p for p in paginas if p in admin_pages]

        if usuario_master():
            return cliente, admin

        return cliente, []

    except Exception:
        return paginas, []

# --------------------------------------------------
# PORTAL DO CLIENTE ENTERPRISE - v1.39.1
# --------------------------------------------------

SUPORTE_CLIENTE_ARQUIVO = Path("SUPORTE_CLIENTE_EIROX.csv")


def usuario_pode_ver_portal_cliente():
    return True


def _portal_data_hora():
    try:
        return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def _portal_numero_br(valor, casas=2):
    try:
        return f"{float(valor):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00"


def _portal_percentual(valor):
    try:
        valor = float(valor)
        return max(min(valor, 100), 0)
    except Exception:
        return 0


def _portal_barra_consumo(valor):
    try:
        valor = _portal_percentual(valor)
        cheios = int(round(valor / 10))
        vazios = 10 - cheios
        return "█" * cheios + "░" * vazios + f" {valor:.0f}%"
    except Exception:
        return "░░░░░░░░░░ 0%"


def portal_empresa_atual():
    try:
        empresa_id = empresa_contexto_atual() if "empresa_contexto_atual" in globals() else st.session_state.get("empresa_id_usuario", "1")
        empresa_nome = obter_nome_empresa(empresa_id) if "obter_nome_empresa" in globals() else "Empresa não identificada"
        return str(empresa_id), str(empresa_nome)
    except Exception:
        return "1", "Empresa não identificada"


def portal_dados_cliente():
    try:
        empresa_id, empresa_nome = portal_empresa_atual()

        dados = {
            "EmpresaID": empresa_id,
            "Cliente": empresa_nome,
            "CNPJ": "",
            "Cidade": "",
            "UF": "",
            "Qtd_Lojas": "",
            "Plano": plano_empresa_contexto() if "plano_empresa_contexto" in globals() else "Starter",
            "Status": "",
            "Data_Implantacao": "",
            "Data_Renovacao": "",
            "Responsavel_Comercial": "",
            "Observacao": ""
        }

        if "carregar_clientes_eirox" in globals():
            clientes = carregar_clientes_eirox()
            if isinstance(clientes, pd.DataFrame) and not clientes.empty and "EmpresaID" in clientes.columns:
                linha = clientes[clientes["EmpresaID"].astype(str).str.strip() == str(empresa_id)]
                if not linha.empty:
                    dados.update(linha.iloc[0].to_dict())

        return dados

    except Exception:
        return {}


def portal_metricas_licenca():
    try:
        empresa_id, _ = portal_empresa_atual()

        if "licenca_metricas_empresa" in globals():
            return licenca_metricas_empresa(empresa_id)

        return {
            "Licenca": {},
            "Status": {},
            "MaxUsuarios": 0,
            "MaxLojas": 0,
            "UsuariosUsados": 0,
            "LojasUsadas": 0,
            "UsuariosDisponiveis": 0,
            "LojasDisponiveis": 0
        }

    except Exception:
        return {
            "Licenca": {},
            "Status": {},
            "MaxUsuarios": 0,
            "MaxLojas": 0,
            "UsuariosUsados": 0,
            "LojasUsadas": 0,
            "UsuariosDisponiveis": 0,
            "LojasDisponiveis": 0
        }


def portal_metricas_uso():
    try:
        empresa_id, _ = portal_empresa_atual()

        logs = carregar_logs_acesso() if "carregar_logs_acesso" in globals() else pd.DataFrame()

        total_acessos = 0
        usuarios_ativos = 0
        ultimo_acesso = "-"

        if isinstance(logs, pd.DataFrame) and not logs.empty:
            logs_empresa = logs.copy()

            if "EmpresaID" in logs_empresa.columns:
                logs_empresa = logs_empresa[logs_empresa["EmpresaID"].astype(str).str.strip() == str(empresa_id)]

            total_acessos = len(logs_empresa)

            if "Usuario" in logs_empresa.columns:
                usuarios_ativos = logs_empresa["Usuario"].astype(str).nunique()

            if "Data_Hora_dt" in logs_empresa.columns and logs_empresa["Data_Hora_dt"].notna().any():
                ultimo_acesso = logs_empresa["Data_Hora_dt"].max().strftime("%d/%m/%Y %H:%M:%S")
            elif "Data_Hora" in logs_empresa.columns and not logs_empresa.empty:
                ultimo_acesso = str(logs_empresa.tail(1).iloc[0].get("Data_Hora", "-"))

        produtos_monitorados = 0
        recomendacoes_ia = 0
        alertas = 0

        try:
            base = globals().get("df", pd.DataFrame())
            if isinstance(base, pd.DataFrame) and not base.empty:
                if "EmpresaID" in base.columns:
                    base = base[base["EmpresaID"].astype(str).str.strip() == str(empresa_id)]

                if "EAN" in base.columns:
                    produtos_monitorados = int(base["EAN"].astype(str).nunique())
                else:
                    produtos_monitorados = int(len(base))
        except Exception:
            pass

        try:
            hist_ia = carregar_historico_ia_pricing() if "carregar_historico_ia_pricing" in globals() else pd.DataFrame()
            if isinstance(hist_ia, pd.DataFrame) and not hist_ia.empty:
                if "EmpresaID" in hist_ia.columns:
                    hist_ia = hist_ia[hist_ia["EmpresaID"].astype(str).str.strip() == str(empresa_id)]
                recomendacoes_ia = len(hist_ia)
        except Exception:
            pass

        try:
            hist_alertas = carregar_historico_alertas() if "carregar_historico_alertas" in globals() else pd.DataFrame()
            if isinstance(hist_alertas, pd.DataFrame) and not hist_alertas.empty:
                if "EmpresaID" in hist_alertas.columns:
                    hist_alertas = hist_alertas[hist_alertas["EmpresaID"].astype(str).str.strip() == str(empresa_id)]
                alertas = len(hist_alertas)
        except Exception:
            pass

        return {
            "UltimoAcesso": ultimo_acesso,
            "UsuariosAtivos": usuarios_ativos,
            "TotalAcessos": total_acessos,
            "ProdutosMonitorados": produtos_monitorados,
            "RecomendacoesIA": recomendacoes_ia,
            "Alertas": alertas
        }

    except Exception:
        return {
            "UltimoAcesso": "-",
            "UsuariosAtivos": 0,
            "TotalAcessos": 0,
            "ProdutosMonitorados": 0,
            "RecomendacoesIA": 0,
            "Alertas": 0
        }


def carregar_chamados_suporte_cliente():
    try:
        if not SUPORTE_CLIENTE_ARQUIVO.exists():
            return pd.DataFrame(columns=[
                "ID", "Data_Hora", "EmpresaID", "Empresa", "Usuario",
                "Assunto", "Prioridade", "Status", "Mensagem", "Versao"
            ])

        return pd.read_csv(
            SUPORTE_CLIENTE_ARQUIVO,
            sep=";",
            encoding="utf-8-sig",
            dtype=str
        ).fillna("")

    except Exception:
        return pd.DataFrame()


def salvar_chamado_suporte_cliente(assunto, prioridade, mensagem):
    try:
        empresa_id, empresa_nome = portal_empresa_atual()

        base = carregar_chamados_suporte_cliente()

        novo = {
            "ID": f"SUP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "Data_Hora": _portal_data_hora(),
            "EmpresaID": empresa_id,
            "Empresa": empresa_nome,
            "Usuario": st.session_state.get("usuario", ""),
            "Assunto": str(assunto).strip(),
            "Prioridade": str(prioridade).strip(),
            "Status": "Aberto",
            "Mensagem": str(mensagem).strip(),
            "Versao": VERSAO_APP
        }

        final = pd.concat([base, pd.DataFrame([novo])], ignore_index=True)

        final.to_csv(
            SUPORTE_CLIENTE_ARQUIVO,
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        try:
            enviar_alerta_telegram(
                "🎫 <b>Novo chamado no Portal do Cliente</b>\\n\\n"
                f"🏢 <b>Empresa:</b> {empresa_nome}\\n"
                f"👤 <b>Usuário:</b> {st.session_state.get('usuario', '')}\\n"
                f"📌 <b>Assunto:</b> {assunto}\\n"
                f"⚠️ <b>Prioridade:</b> {prioridade}\\n"
                f"🕒 <b>Horário:</b> {_portal_data_hora()}\\n"
                f"🏷️ <b>Versão:</b> {VERSAO_APP}"
            )
        except Exception:
            pass

        return True, "Chamado aberto com sucesso."

    except Exception as erro:
        return False, f"Erro ao abrir chamado: {erro}"


def portal_novidades():
    return pd.DataFrame(
        [
            {"Versão": "v1.39.1", "Novidade": "Portal do Cliente Enterprise", "Descrição": "Minha empresa, licença, uso, suporte e central de conhecimento."},
            {"Versão": "v1.38.1", "Novidade": "Menu por plano", "Descrição": "Área do Cliente separada da Administração Eirox."},
            {"Versão": "v1.38.0", "Novidade": "CRM Enterprise", "Descrição": "Gestão comercial de clientes, planos, MRR e implantação."},
            {"Versão": "v1.37.1", "Novidade": "Workflow Comercial", "Descrição": "Aprovação e rejeição de recomendações da IA."},
            {"Versão": "v1.37.0", "Novidade": "IA Pricing Enterprise", "Descrição": "Recomendações automáticas de preço."},
            {"Versão": "v1.36.2", "Novidade": "Motor de Oportunidades", "Descrição": "Ranking financeiro de oportunidades comerciais."}
        ]
    )




# --------------------------------------------------
# BILLING ENTERPRISE - v1.40.0
# --------------------------------------------------

BILLING_EIROX_ARQUIVO = Path("BILLING_EIROX.csv")


PLANOS_BILLING_EIROX = {
    "Starter": {
        "Mensalidade": 490,
        "MaxUsuarios": 5,
        "MaxLojas": 10
    },
    "Professional": {
        "Mensalidade": 1290,
        "MaxUsuarios": 20,
        "MaxLojas": 50
    },
    "Enterprise": {
        "Mensalidade": 2990,
        "MaxUsuarios": 100,
        "MaxLojas": 500
    },
    "Enterprise Plus": {
        "Mensalidade": 5990,
        "MaxUsuarios": 9999,
        "MaxLojas": 9999
    }
}


def usuario_pode_ver_billing_enterprise():
    try:
        return usuario_master()
    except Exception:
        return str(st.session_state.get("usuario", "")).strip().lower() == "paulomarques"


def _billing_data_hora():
    try:
        return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def _billing_numero_br(valor, casas=2):
    try:
        return f"{float(valor):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00"


def _billing_parse_numero(valor):
    try:
        return float(str(valor).replace("R$", "").replace(" ", "").replace(".", "").replace(",", "."))
    except Exception:
        return 0.0


def _billing_dias_vencimento(data_vencimento):
    try:
        dt = pd.to_datetime(str(data_vencimento), dayfirst=True, errors="coerce")
        if pd.isna(dt):
            return None
        hoje = pd.Timestamp.now().normalize()
        return int((dt.normalize() - hoje).days)
    except Exception:
        return None


def inicializar_billing_eirox():
    try:
        if not BILLING_EIROX_ARQUIVO.exists():
            hoje = datetime.now(ZoneInfo("America/Sao_Paulo"))

            base = pd.DataFrame(
                [
                    {
                        "FaturaID": "FAT-0001",
                        "EmpresaID": "1",
                        "Cliente": "Marabá - Cliente teste",
                        "Plano": "Enterprise",
                        "Valor_Mensal": str(PLANOS_BILLING_EIROX["Enterprise"]["Mensalidade"]),
                        "Data_Emissao": hoje.strftime("%d/%m/%Y"),
                        "Data_Vencimento": (hoje + pd.DateOffset(days=30)).strftime("%d/%m/%Y"),
                        "Data_Pagamento": "",
                        "Status": "Em aberto",
                        "Ciclo": "Mensal",
                        "Forma_Pagamento": "",
                        "Observacao": "Fatura inicial de teste",
                        "Criado_Em": _billing_data_hora()
                    },
                    {
                        "FaturaID": "FAT-0002",
                        "EmpresaID": "2",
                        "Cliente": "Belém - Cliente teste",
                        "Plano": "Starter",
                        "Valor_Mensal": str(PLANOS_BILLING_EIROX["Starter"]["Mensalidade"]),
                        "Data_Emissao": hoje.strftime("%d/%m/%Y"),
                        "Data_Vencimento": (hoje + pd.DateOffset(days=30)).strftime("%d/%m/%Y"),
                        "Data_Pagamento": "",
                        "Status": "Trial",
                        "Ciclo": "Mensal",
                        "Forma_Pagamento": "",
                        "Observacao": "Fatura inicial de teste",
                        "Criado_Em": _billing_data_hora()
                    }
                ]
            )

            base.to_csv(
                BILLING_EIROX_ARQUIVO,
                index=False,
                sep=";",
                encoding="utf-8-sig"
            )

        return True

    except Exception:
        return False


@st.cache_data(ttl=60, show_spinner=False)
def carregar_billing_eirox():
    try:
        inicializar_billing_eirox()

        base = pd.read_csv(
            BILLING_EIROX_ARQUIVO,
            sep=";",
            encoding="utf-8-sig",
            dtype=str
        ).fillna("")

        obrigatorias = [
            "FaturaID",
            "EmpresaID",
            "Cliente",
            "Plano",
            "Valor_Mensal",
            "Data_Emissao",
            "Data_Vencimento",
            "Data_Pagamento",
            "Status",
            "Ciclo",
            "Forma_Pagamento",
            "Observacao",
            "Criado_Em"
        ]

        for col in obrigatorias:
            if col not in base.columns:
                base[col] = ""

        return base[obrigatorias].copy()

    except Exception:
        return pd.DataFrame()


def salvar_billing_eirox(base):
    try:
        base = base.copy().astype(str)

        base.to_csv(
            BILLING_EIROX_ARQUIVO,
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        try:
            carregar_billing_eirox.clear()
        except Exception:
            pass

        return True

    except Exception:
        return False


def gerar_id_fatura():
    try:
        base = carregar_billing_eirox()
        if base.empty:
            return "FAT-0001"

        nums = []
        for x in base["FaturaID"].astype(str).tolist():
            m = re.search(r'(\d+)$', x)
            if m:
                nums.append(int(m.group(1)))

        prox = max(nums) + 1 if nums else len(base) + 1
        return f"FAT-{prox:04d}"

    except Exception:
        return f"FAT-{datetime.now().strftime('%Y%m%d%H%M%S')}"


def criar_ou_atualizar_fatura_eirox(
    fatura_id,
    empresa_id,
    cliente,
    plano,
    valor_mensal,
    data_emissao,
    data_vencimento,
    data_pagamento,
    status,
    ciclo,
    forma_pagamento,
    observacao
):
    try:
        fatura_id = str(fatura_id).strip() or gerar_id_fatura()
        empresa_id = str(empresa_id).strip()
        cliente = str(cliente).strip()

        if not empresa_id or not cliente:
            return False, "EmpresaID e Cliente são obrigatórios."

        base = carregar_billing_eirox()

        linha = {
            "FaturaID": fatura_id,
            "EmpresaID": empresa_id,
            "Cliente": cliente,
            "Plano": str(plano).strip(),
            "Valor_Mensal": str(valor_mensal).strip(),
            "Data_Emissao": str(data_emissao).strip(),
            "Data_Vencimento": str(data_vencimento).strip(),
            "Data_Pagamento": str(data_pagamento).strip(),
            "Status": str(status).strip(),
            "Ciclo": str(ciclo).strip(),
            "Forma_Pagamento": str(forma_pagamento).strip(),
            "Observacao": str(observacao).strip(),
            "Criado_Em": _billing_data_hora()
        }

        if not base.empty and fatura_id in base["FaturaID"].astype(str).tolist():
            idx = base.index[base["FaturaID"].astype(str) == fatura_id][0]
            for k, v in linha.items():
                if k != "Criado_Em":
                    base.loc[idx, k] = v
            acao = "Atualização de fatura"
        else:
            base = pd.concat([base, pd.DataFrame([linha])], ignore_index=True)
            acao = "Criação de fatura"

        salvar_billing_eirox(base)

        try:
            registrar_log_usuario(
                acao,
                fatura_id,
                f"Cliente={cliente} | Plano={plano} | Valor={valor_mensal} | Status={status}"
            )
        except Exception:
            pass

        try:
            enviar_alerta_telegram(
                "💳 <b>Billing Eirox atualizado</b>\\n\\n"
                f"📄 <b>Fatura:</b> {fatura_id}\\n"
                f"🏢 <b>Cliente:</b> {cliente}\\n"
                f"📦 <b>Plano:</b> {plano}\\n"
                f"💰 <b>Valor:</b> R$ {_billing_numero_br(_billing_parse_numero(valor_mensal))}\\n"
                f"🔐 <b>Status:</b> {status}\\n"
                f"👤 <b>Usuário:</b> {st.session_state.get('usuario', '')}\\n"
                f"🕒 <b>Horário:</b> {_billing_data_hora()}\\n"
                f"🏷️ <b>Versão:</b> {VERSAO_APP}"
            )
        except Exception:
            pass

        return True, f"{acao} realizada com sucesso."

    except Exception as erro:
        return False, f"Erro ao salvar fatura: {erro}"


def metricas_billing_enterprise():
    try:
        base = carregar_billing_eirox()

        if base.empty:
            return {
                "Faturas": 0,
                "EmAberto": 0,
                "Pagas": 0,
                "Vencidas": 0,
                "Trial": 0,
                "MRR": 0,
                "ARR": 0,
                "ReceitaPaga": 0
            }

        b = base.copy()

        valores = b["Valor_Mensal"].apply(_billing_parse_numero)

        dias = b["Data_Vencimento"].apply(_billing_dias_vencimento)

        status = b["Status"].astype(str).str.lower()

        vencidas_mask = (dias < 0) & (~status.isin(["paga", "cancelada"]))

        mrr_mask = status.isin(["em aberto", "paga", "trial"])
        mrr = float(valores[mrr_mask].sum())

        pagas = status.eq("paga")

        return {
            "Faturas": int(len(b)),
            "EmAberto": int(status.eq("em aberto").sum()),
            "Pagas": int(pagas.sum()),
            "Vencidas": int(vencidas_mask.sum()),
            "Trial": int(status.eq("trial").sum()),
            "MRR": mrr,
            "ARR": mrr * 12,
            "ReceitaPaga": float(valores[pagas].sum())
        }

    except Exception:
        return {
            "Faturas": 0,
            "EmAberto": 0,
            "Pagas": 0,
            "Vencidas": 0,
            "Trial": 0,
            "MRR": 0,
            "ARR": 0,
            "ReceitaPaga": 0
        }


def atualizar_licenca_por_billing(empresa_id, cliente, plano, status_financeiro):
    """
    Integra billing com licenciamento.
    Se inadimplente/suspenso/cancelado, bloqueia licença.
    Se pago/em aberto/trial, mantém licença ativa/trial.
    """

    try:
        if "criar_ou_atualizar_licenca" not in globals():
            return False, "Licenciamento não disponível."

        hoje = datetime.now(ZoneInfo("America/Sao_Paulo"))

        if str(status_financeiro).lower() in ["vencida", "suspenso", "cancelada", "inadimplente"]:
            status_lic = "Bloqueada"
        elif str(status_financeiro).lower() == "trial":
            status_lic = "Trial"
        else:
            status_lic = "Ativa"

        data_inicio = hoje.strftime("%d/%m/%Y")
        data_expiracao = (hoje + pd.DateOffset(days=30)).strftime("%d/%m/%Y")

        return criar_ou_atualizar_licenca(
            empresa_id,
            cliente,
            plano,
            data_inicio,
            data_expiracao,
            status_lic,
            f"Atualizado automaticamente pelo Billing Enterprise em {_billing_data_hora()}"
        )

    except Exception as erro:
        return False, str(erro)


def faturamento_por_plano():
    try:
        base = carregar_billing_eirox()
        if base.empty:
            return pd.DataFrame()

        b = base.copy()
        b["Valor_Num"] = b["Valor_Mensal"].apply(_billing_parse_numero)

        return (
            b.groupby("Plano", dropna=False)
            .agg(
                Faturas=("FaturaID", "count"),
                Receita=("Valor_Num", "sum")
            )
            .reset_index()
            .sort_values("Receita", ascending=False)
        )

    except Exception:
        return pd.DataFrame()


def faturamento_por_cliente():
    try:
        base = carregar_billing_eirox()
        if base.empty:
            return pd.DataFrame()

        b = base.copy()
        b["Valor_Num"] = b["Valor_Mensal"].apply(_billing_parse_numero)

        return (
            b.groupby(["EmpresaID", "Cliente"], dropna=False)
            .agg(
                Faturas=("FaturaID", "count"),
                Receita=("Valor_Num", "sum")
            )
            .reset_index()
            .sort_values("Receita", ascending=False)
        )

    except Exception:
        return pd.DataFrame()



# --------------------------------------------------
# LOGIN E CONTROLE DE ACESSO
# --------------------------------------------------

USUARIOS = {
    "admin": {
        "senha_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "nome": "Administrador",
        "perfil": "Diretoria"
    },
    "paulo": {
        "senha_hash": hashlib.sha256("paulo123".encode()).hexdigest(),
        "nome": "Paulo Marques",
        "perfil": "Diretoria"
    },
    "paulomarques": {
        "senha_hash": hashlib.sha256("031730".encode()).hexdigest(),
        "nome": "Paulo Marques",
        "perfil": "Diretoria"
    },
    "vanderlei": {
        "senha_hash": hashlib.sha256("031730".encode()).hexdigest(),
        "nome": "Vanderlei",
        "perfil": "Diretoria"
    },
    "ubiratan": {
        "senha_hash": hashlib.sha256("031730".encode()).hexdigest(),
        "nome": "Ubiratan",
        "perfil": "Diretoria"
    },

    "pricing": {
        "senha_hash": hashlib.sha256("pricing123".encode()).hexdigest(),
        "nome": "Equipe Pricing",
        "perfil": "Pricing"
    },
    "comercial": {
        "senha_hash": hashlib.sha256("comercial123".encode()).hexdigest(),
        "nome": "Equipe Comercial",
        "perfil": "Comercial"
    },
    "regional": {
        "senha_hash": hashlib.sha256("regional123".encode()).hexdigest(),
        "nome": "Gerente Regional",
        "perfil": "Regional"
    },
    "consulta": {
        "senha_hash": hashlib.sha256("consulta123".encode()).hexdigest(),
        "nome": "Consulta",
        "perfil": "Consulta"
    }
}




# --------------------------------------------------
# GESTÃO DINÂMICA DE USUÁRIOS - HOMOLOGAÇÃO v1.35
# --------------------------------------------------

USUARIOS_ARQUIVO = Path("USUARIOS_EIROX.csv")
USUARIOS_LOG_ARQUIVO = Path("logs") / "log_usuarios.csv"


def _agora_brasil_txt():
    try:
        return horario_brasil_formatado()
    except Exception:
        return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def registrar_log_usuario(acao, usuario_alvo="", detalhe=""):
    """
    Registra alterações feitas no cadastro de usuários.
    """

    try:
        Path("logs").mkdir(exist_ok=True)

        linha = {
            "Data_Hora": _agora_brasil_txt(),
            "Administrador": st.session_state.get("usuario", ""),
            "Usuario_Alvo": str(usuario_alvo),
            "Acao": str(acao),
            "Detalhe": str(detalhe),
            "Versao": VERSAO_APP
        }

        existe = USUARIOS_LOG_ARQUIVO.exists()

        with open(USUARIOS_LOG_ARQUIVO, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(linha.keys()), delimiter=";")

            if not existe:
                writer.writeheader()

            writer.writerow(linha)

    except Exception:
        pass


def _usuarios_padrao_dataframe():
    """
    Migra os usuários fixos do código para a base USUARIOS_EIROX.csv.
    """

    linhas = []

    for usuario, dados in USUARIOS.items():
        linhas.append(
            {
                "Usuario": str(usuario).strip().lower(),
                "Nome": str(dados.get("nome", "")),
                "Perfil": str(dados.get("perfil", "Consulta")),
                "Senha_Hash": str(dados.get("senha_hash", "")),
                "Ativo": "Sim",
                "Expira_Em": "",
                "Forcar_Reset": "Não",
                "EmpresaID": "1",
                "Criado_Em": _agora_brasil_txt(),
                "Atualizado_Em": _agora_brasil_txt()
            }
        )

    return pd.DataFrame(linhas)


def inicializar_arquivo_usuarios():
    """
    Cria o arquivo de usuários dinâmico caso ainda não exista.
    """

    try:
        if not USUARIOS_ARQUIVO.exists():
            base = _usuarios_padrao_dataframe()
            base.to_csv(
                USUARIOS_ARQUIVO,
                index=False,
                sep=";",
                encoding="utf-8-sig"
            )

        return True

    except Exception:
        return False


@st.cache_data(ttl=60, show_spinner=False)
def carregar_usuarios_sistema():
    """
    Carrega usuários dinâmicos.
    """

    try:
        inicializar_arquivo_usuarios()

        base = pd.read_csv(
            USUARIOS_ARQUIVO,
            sep=";",
            encoding="utf-8-sig",
            dtype=str
        ).fillna("")

        base.columns = base.columns.astype(str).str.strip()

        obrigatorias = [
            "Usuario",
            "Nome",
            "Perfil",
            "Senha_Hash",
            "Ativo",
            "Expira_Em",
            "Forcar_Reset",
            "EmpresaID",
            "Criado_Em",
            "Atualizado_Em"
        ]

        for col in obrigatorias:
            if col not in base.columns:
                base[col] = ""

        base["Usuario"] = base["Usuario"].astype(str).str.strip().str.lower()
        base["Ativo"] = base["Ativo"].replace("", "Sim")
        base["Forcar_Reset"] = base["Forcar_Reset"].replace("", "Não")

        return base[obrigatorias].copy()

    except Exception:
        return _usuarios_padrao_dataframe()


def salvar_usuarios_sistema(base):
    """
    Salva a base dinâmica de usuários.
    """

    try:
        base = base.copy()
        base["Usuario"] = base["Usuario"].astype(str).str.strip().str.lower()

        base.to_csv(
            USUARIOS_ARQUIVO,
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        try:
            carregar_usuarios_sistema.clear()
        except Exception:
            pass

        return True

    except Exception:
        return False


def usuario_expirado(expira_em):
    """
    Verifica se o usuário está expirado.
    Formato: dd/mm/aaaa.
    """

    try:
        expira_em = str(expira_em).strip()

        if not expira_em:
            return False

        data_exp = pd.to_datetime(
            expira_em,
            dayfirst=True,
            errors="coerce"
        )

        if pd.isna(data_exp):
            return False

        hoje = pd.Timestamp.now().normalize()

        return data_exp.normalize() < hoje

    except Exception:
        return False


def obter_dados_usuario(usuario):
    """
    Busca usuário na base dinâmica.
    """

    try:
        usuario = str(usuario).strip().lower()
        base = carregar_usuarios_sistema()
        linha = base[base["Usuario"] == usuario]

        if linha.empty:
            return None

        return linha.iloc[0].to_dict()

    except Exception:
        return None


def usuario_pode_gerenciar_usuarios():
    """
    Gestão de usuários exclusiva inicialmente para paulomarques.
    """

    try:
        return str(st.session_state.get("usuario", "")).strip().lower() == "paulomarques"
    except Exception:
        return False


def criar_ou_atualizar_usuario(usuario, nome, perfil, senha=None, ativo="Sim", expira_em="", forcar_reset="Não", empresa_id="1"):
    """
    Cria ou atualiza usuário na base dinâmica.
    """

    try:
        usuario = str(usuario).strip().lower()
        nome = str(nome).strip()
        perfil = str(perfil).strip()
        ativo = str(ativo).strip()
        expira_em = str(expira_em).strip()
        forcar_reset = str(forcar_reset).strip()
        empresa_id = str(empresa_id).strip() or "1"

        if not usuario or not nome or not perfil:
            return False, "Usuário, nome e perfil são obrigatórios."

        base = carregar_usuarios_sistema()
        existe = base["Usuario"].eq(usuario).any()
        agora = _agora_brasil_txt()

        if existe:
            idx = base.index[base["Usuario"] == usuario][0]

            base.loc[idx, "Nome"] = nome
            base.loc[idx, "Perfil"] = perfil
            base.loc[idx, "Ativo"] = ativo
            base.loc[idx, "Expira_Em"] = expira_em
            base.loc[idx, "Forcar_Reset"] = forcar_reset
            base.loc[idx, "EmpresaID"] = empresa_id
            base.loc[idx, "Atualizado_Em"] = agora

            if senha:
                base.loc[idx, "Senha_Hash"] = hashlib.sha256(str(senha).encode()).hexdigest()
                detalhe = "Usuário atualizado com reset de senha."
            else:
                detalhe = "Usuário atualizado."

            salvar_usuarios_sistema(base)
            registrar_log_usuario("Atualização", usuario, detalhe)

            try:
                enviar_alerta_telegram(
                    "👥 <b>Usuário atualizado no Eirox</b>\n\n"
                    f"👤 <b>Usuário:</b> {usuario}\n"
                    f"🔐 <b>Perfil:</b> {perfil}\n"
                    f"✅ <b>Ativo:</b> {ativo}\n"
                    f"🕒 <b>Horário:</b> {_agora_brasil_txt()}\n"
                    f"🙋 <b>Administrador:</b> {st.session_state.get('usuario', '')}"
                )
            except Exception:
                pass

            return True, detalhe

        if not senha:
            return False, "Senha obrigatória para novo usuário."

        nova_linha = {
            "Usuario": usuario,
            "Nome": nome,
            "Perfil": perfil,
            "Senha_Hash": hashlib.sha256(str(senha).encode()).hexdigest(),
            "Ativo": ativo,
            "Expira_Em": expira_em,
            "Forcar_Reset": forcar_reset,
            "EmpresaID": empresa_id,
            "Criado_Em": agora,
            "Atualizado_Em": agora
        }

        base = pd.concat(
            [
                base,
                pd.DataFrame([nova_linha])
            ],
            ignore_index=True
        )

        salvar_usuarios_sistema(base)
        registrar_log_usuario("Criação", usuario, "Usuário criado.")

        try:
            enviar_alerta_telegram(
                "👥 <b>Novo usuário criado no Eirox</b>\n\n"
                f"👤 <b>Usuário:</b> {usuario}\n"
                f"🙋 <b>Nome:</b> {nome}\n"
                f"🔐 <b>Perfil:</b> {perfil}\n"
                f"✅ <b>Ativo:</b> {ativo}\n"
                f"🕒 <b>Horário:</b> {_agora_brasil_txt()}\n"
                f"🧑‍💼 <b>Administrador:</b> {st.session_state.get('usuario', '')}"
            )
        except Exception:
            pass

        return True, "Usuário criado com sucesso."

    except Exception as erro:
        return False, f"Erro ao salvar usuário: {erro}"


def bloquear_desbloquear_usuario(usuario, ativo):
    """
    Bloqueia ou desbloqueia usuário.
    """

    try:
        usuario = str(usuario).strip().lower()
        base = carregar_usuarios_sistema()

        if usuario not in base["Usuario"].tolist():
            return False, "Usuário não encontrado."

        idx = base.index[base["Usuario"] == usuario][0]
        base.loc[idx, "Ativo"] = "Sim" if ativo else "Não"
        base.loc[idx, "Atualizado_Em"] = _agora_brasil_txt()

        salvar_usuarios_sistema(base)

        acao = "Desbloqueio" if ativo else "Bloqueio"
        registrar_log_usuario(acao, usuario, f"Ativo={base.loc[idx, 'Ativo']}")

        try:
            enviar_alerta_telegram(
                f"{'🔓' if ativo else '🔒'} <b>{acao} de usuário no Eirox</b>\n\n"
                f"👤 <b>Usuário:</b> {usuario}\n"
                f"✅ <b>Ativo:</b> {base.loc[idx, 'Ativo']}\n"
                f"🕒 <b>Horário:</b> {_agora_brasil_txt()}\n"
                f"🧑‍💼 <b>Administrador:</b> {st.session_state.get('usuario', '')}"
            )
        except Exception:
            pass

        return True, f"Usuário {'desbloqueado' if ativo else 'bloqueado'} com sucesso."

    except Exception as erro:
        return False, f"Erro ao alterar status: {erro}"


def resetar_senha_usuario(usuario, nova_senha, forcar_reset="Não"):
    """
    Reseta senha do usuário.
    """

    try:
        usuario = str(usuario).strip().lower()

        if not nova_senha:
            return False, "Informe a nova senha."

        base = carregar_usuarios_sistema()

        if usuario not in base["Usuario"].tolist():
            return False, "Usuário não encontrado."

        idx = base.index[base["Usuario"] == usuario][0]
        base.loc[idx, "Senha_Hash"] = hashlib.sha256(str(nova_senha).encode()).hexdigest()
        base.loc[idx, "Forcar_Reset"] = forcar_reset
        base.loc[idx, "Atualizado_Em"] = _agora_brasil_txt()

        salvar_usuarios_sistema(base)
        registrar_log_usuario("Reset de senha", usuario, f"Forcar_Reset={forcar_reset}")

        try:
            enviar_alerta_telegram(
                "🔑 <b>Reset de senha no Eirox</b>\n\n"
                f"👤 <b>Usuário:</b> {usuario}\n"
                f"🔁 <b>Forçar reset:</b> {forcar_reset}\n"
                f"🕒 <b>Horário:</b> {_agora_brasil_txt()}\n"
                f"🧑‍💼 <b>Administrador:</b> {st.session_state.get('usuario', '')}"
            )
        except Exception:
            pass

        return True, "Senha redefinida com sucesso."

    except Exception as erro:
        return False, f"Erro ao redefinir senha: {erro}"


def carregar_log_usuarios():
    """
    Carrega log de alterações de usuários.
    """

    try:
        if not USUARIOS_LOG_ARQUIVO.exists():
            return pd.DataFrame()

        return pd.read_csv(
            USUARIOS_LOG_ARQUIVO,
            sep=";",
            encoding="utf-8-sig"
        )

    except Exception:
        return pd.DataFrame()



PERMISSOES_TELAS = {
    "Diretoria": [
        "📊 Dashboard Geral",
        "🔎 Rede/Loja vs Concorrentes",
        "🛒 Negociação Compras",
        "🌎 Mapa Geográfico de Concorrência",
        "🚨 Central de Alertas",
        "📈 Simulador Inteligente",
        "🏢 Dashboard Executivo",
        "🎯 Sugestão de Pesquisa",
        "🧪 Diagnóstico"
    ],
    "Pricing": [
        "📊 Dashboard Geral",
        "🔎 Rede/Loja vs Concorrentes",
        "🛒 Negociação Compras",
        "🌎 Mapa Geográfico de Concorrência",
        "🚨 Central de Alertas",
        "📈 Simulador Inteligente",
        "🏢 Dashboard Executivo",
        "🎯 Sugestão de Pesquisa",
        "🧪 Diagnóstico"
    ],
    "Comercial": [
        "📊 Dashboard Geral",
        "🔎 Rede/Loja vs Concorrentes",
        "🛒 Negociação Compras",
        "🌎 Mapa Geográfico de Concorrência",
        "🚨 Central de Alertas",
        "📈 Simulador Inteligente",
        "🏢 Dashboard Executivo",
        "🎯 Sugestão de Pesquisa",
        "🧪 Diagnóstico"
    ],
    "Regional": [
        "📊 Dashboard Geral",
        "🔎 Rede/Loja vs Concorrentes",
        "🛒 Negociação Compras",
        "🌎 Mapa Geográfico de Concorrência",
        "🚨 Central de Alertas",
        "📈 Simulador Inteligente",
        "🏢 Dashboard Executivo",
        "🎯 Sugestão de Pesquisa",
        "🧪 Diagnóstico"
    ],
    "Consulta": [
        "📊 Dashboard Geral",
        "🏢 Dashboard Executivo"
    ]
}



def iniciar_auditoria_sessao(usuario, nome, perfil):
    """
    Inicializa controle de navegação do usuário na sessão atual.
    """

    try:
        agora = horario_brasil_formatado()

        if not st.session_state.get("auditoria_sessao_iniciada", False):

            st.session_state["auditoria_sessao_iniciada"] = True
            st.session_state["auditoria_usuario"] = usuario
            st.session_state["auditoria_nome"] = nome
            st.session_state["auditoria_perfil"] = perfil
            st.session_state["auditoria_entrada"] = agora
            st.session_state["auditoria_ultima_acao"] = agora
            st.session_state["auditoria_paginas"] = []
            st.session_state["auditoria_paginas_unicas"] = []
            st.session_state["auditoria_contador_paginas"] = 0

    except Exception:
        pass


def registrar_pagina_acessada(pagina):
    """
    Registra cada navegação entre telas.
    """

    try:
        if not st.session_state.get("logado", False):
            return

        agora = horario_brasil_formatado()

        if "auditoria_paginas" not in st.session_state:
            st.session_state["auditoria_paginas"] = []

        if "auditoria_paginas_unicas" not in st.session_state:
            st.session_state["auditoria_paginas_unicas"] = []

        pagina_limpa = str(pagina).strip()

        if not pagina_limpa:
            return

        ultima_pagina = st.session_state["auditoria_paginas"][-1]["pagina"] if st.session_state["auditoria_paginas"] else None

        if pagina_limpa != ultima_pagina:

            st.session_state["auditoria_paginas"].append(
                {
                    "pagina": pagina_limpa,
                    "horario": agora
                }
            )

            if pagina_limpa not in st.session_state["auditoria_paginas_unicas"]:
                st.session_state["auditoria_paginas_unicas"].append(pagina_limpa)

            st.session_state["auditoria_contador_paginas"] = len(
                st.session_state["auditoria_paginas"]
            )

        st.session_state["auditoria_ultima_acao"] = agora
        st.session_state["auditoria_ultima_pagina"] = pagina_limpa

    except Exception:
        pass


def calcular_tempo_sessao():
    """
    Calcula tempo aproximado entre entrada e última ação.
    """

    try:
        entrada_txt = st.session_state.get("auditoria_entrada")
        ultima_txt = st.session_state.get("auditoria_ultima_acao")

        if not entrada_txt or not ultima_txt:
            return "Não disponível"

        entrada = datetime.strptime(
            entrada_txt,
            "%d/%m/%Y %H:%M:%S"
        )

        ultima = datetime.strptime(
            ultima_txt,
            "%d/%m/%Y %H:%M:%S"
        )

        total_segundos = int(
            max(
                0,
                (ultima - entrada).total_seconds()
            )
        )

        horas = total_segundos // 3600
        minutos = (total_segundos % 3600) // 60
        segundos = total_segundos % 60

        if horas > 0:
            return f"{horas}h {minutos}min {segundos}s"

        if minutos > 0:
            return f"{minutos}min {segundos}s"

        return f"{segundos}s"

    except Exception:
        return "Não disponível"


def montar_resumo_navegacao():
    """
    Monta mensagem de resumo da sessão para Telegram.
    """

    try:
        usuario = st.session_state.get("auditoria_usuario", st.session_state.get("usuario", ""))
        nome = st.session_state.get("auditoria_nome", st.session_state.get("nome_usuario", ""))
        perfil = st.session_state.get("auditoria_perfil", st.session_state.get("perfil_usuario", ""))
        entrada = st.session_state.get("auditoria_entrada", "")
        ultima = st.session_state.get("auditoria_ultima_acao", "")
        ultima_pagina = st.session_state.get("auditoria_ultima_pagina", "")
        paginas_unicas = st.session_state.get("auditoria_paginas_unicas", [])
        paginas = st.session_state.get("auditoria_paginas", [])

        ambiente = "Streamlit Cloud" if "/mount/src" in str(Path.cwd()) else "Localhost"

        lista_paginas = ""

        for i, pag in enumerate(paginas_unicas, start=1):
            lista_paginas += f"{i}. {pag}\n"

        if not lista_paginas:
            lista_paginas = "Nenhuma página registrada\n"

        mensagem = (
            "📊 <b>Resumo de navegação Eirox</b>\n\n"
            f"👤 <b>Usuário:</b> {usuario}\n"
            f"🙋 <b>Nome:</b> {nome}\n"
            f"🔐 <b>Perfil:</b> {perfil}\n\n"
            f"🕒 <b>Entrada:</b> {entrada}\n"
            f"🕘 <b>Última ação:</b> {ultima}\n"
            f"⏱️ <b>Tempo no sistema:</b> {calcular_tempo_sessao()}\n\n"
            f"🧭 <b>Telas navegadas:</b> {len(paginas_unicas)}\n"
            f"🔁 <b>Trocas de tela:</b> {len(paginas)}\n\n"
            f"📍 <b>Última página:</b> {ultima_pagina}\n\n"
            f"📄 <b>Páginas acessadas:</b>\n{lista_paginas}\n"
            f"{texto_localizacao_telegram()}"
            f"🌐 <b>Ambiente:</b> {ambiente}\n"
            f"🏷️ <b>Versão:</b> {VERSAO_APP}"
        )

        return mensagem

    except Exception:
        return ""


def enviar_resumo_navegacao_telegram():
    """
    Envia o resumo da sessão, evitando duplicidade.
    """

    try:
        if st.session_state.get("resumo_navegacao_enviado", False):
            return

        mensagem = montar_resumo_navegacao()

        if mensagem:
            enviado = enviar_alerta_telegram(mensagem)

            if enviado:
                st.session_state["resumo_navegacao_enviado"] = True

    except Exception:
        pass




def enviar_resumo_periodico_navegacao():
    """
    Envia resumo automático durante o uso.
    Isso cobre casos em que o usuário fecha o navegador sem clicar em Sair.

    Regra:
    - Envia no máximo uma vez a cada 5 minutos.
    - Envia também quando houver pelo menos 3 trocas de tela desde o último envio.
    """

    try:
        if not st.session_state.get("logado", False):
            return

        agora_txt = horario_brasil_formatado()

        ultima_envio_txt = st.session_state.get("auditoria_ultimo_resumo_auto")
        trocas_atuais = int(st.session_state.get("auditoria_contador_paginas", 0))
        trocas_ultimo_envio = int(st.session_state.get("auditoria_trocas_ultimo_resumo", 0))

        deve_enviar = False

        if not ultima_envio_txt:
            # Não envia imediatamente no login para evitar duplicar o alerta de entrada.
            st.session_state["auditoria_ultimo_resumo_auto"] = agora_txt
            st.session_state["auditoria_trocas_ultimo_resumo"] = trocas_atuais
            return

        try:
            ultima_envio = datetime.strptime(
                ultima_envio_txt,
                "%d/%m/%Y %H:%M:%S"
            )

            agora = datetime.strptime(
                agora_txt,
                "%d/%m/%Y %H:%M:%S"
            )

            minutos_passados = (
                agora - ultima_envio
            ).total_seconds() / 60

            if minutos_passados >= 5:
                deve_enviar = True

        except Exception:
            pass

        if trocas_atuais - trocas_ultimo_envio >= 3:
            deve_enviar = True

        if not deve_enviar:
            return

        mensagem = montar_resumo_navegacao()

        if mensagem:
            mensagem = mensagem.replace(
                "📊 <b>Resumo de navegação Eirox</b>",
                "📡 <b>Resumo automático de navegação Eirox</b>"
            )

            enviado = enviar_alerta_telegram(mensagem)

            if enviado:
                st.session_state["auditoria_ultimo_resumo_auto"] = agora_txt
                st.session_state["auditoria_trocas_ultimo_resumo"] = trocas_atuais

    except Exception:
        pass



def autenticar_usuario(usuario, senha):

    usuario = str(usuario).strip().lower()

    dados_usuario = obter_dados_usuario(usuario)

    if not dados_usuario:
        return False

    if str(dados_usuario.get("Ativo", "Sim")).strip().lower() != "sim":
        st.session_state["login_bloqueado_motivo"] = "Usuário bloqueado."
        return False

    if usuario_expirado(dados_usuario.get("Expira_Em", "")):
        st.session_state["login_bloqueado_motivo"] = "Acesso expirado."
        return False

    senha_hash = hashlib.sha256(
        str(senha).encode()
    ).hexdigest()

    ok = senha_hash == str(dados_usuario.get("Senha_Hash", ""))

    if ok and str(dados_usuario.get("Forcar_Reset", "Não")).strip().lower() == "sim":
        st.session_state["login_bloqueado_motivo"] = "Senha temporária. Solicite alteração ao administrador."
        return False

    return ok


def tela_login():

    st.markdown(
        """
        <div style="text-align:center; margin-top:30px;">
            <h1>📊 Eirox Pricing</h1>
            <h3 style="font-weight:400; color:#B0B0B0;">
                Ferramenta de Inteligência de Pricing
            </h3>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.form("form_login"):

        usuario = st.text_input(
            "Usuário"
        )

        senha = st.text_input(
            "Senha",
            type="password"
        )

        entrar = st.form_submit_button(
            "Entrar",
            use_container_width=True
        )

    if entrar:

        if autenticar_usuario(
            usuario,
            senha
        ):

            usuario_key = str(usuario).strip().lower()

            licenca_ok, licenca_msg = validar_licenca_login(usuario_key)

            if not licenca_ok:
                st.error(licenca_msg)
                return

            dados_login = obter_dados_usuario(usuario_key)

            st.session_state["logado"] = True
            st.session_state["usuario"] = usuario_key
            st.session_state["nome_usuario"] = dados_login.get("Nome", usuario_key) if dados_login else usuario_key
            st.session_state["perfil_usuario"] = dados_login.get("Perfil", "Consulta") if dados_login else "Consulta"
            st.session_state["empresa_id_usuario"] = dados_login.get("EmpresaID", "1") if dados_login else "1"
            st.session_state["empresa_id_contexto"] = st.session_state["empresa_id_usuario"]

            salvar_log_acesso(
                "Login",
                "Sistema",
                "Usuário autenticado com sucesso"
            )

            registrar_alerta_login(
                usuario_key,
                st.session_state["nome_usuario"],
                st.session_state["perfil_usuario"]
            )

            iniciar_auditoria_sessao(
                usuario_key,
                st.session_state["nome_usuario"],
                st.session_state["perfil_usuario"]
            )

            st.rerun()

        else:

            motivo = st.session_state.pop("login_bloqueado_motivo", "")

            if motivo:
                st.error(motivo)
            else:
                st.error(
                    "Usuário ou senha inválidos."
                )


def exigir_login():

    if "logado" not in st.session_state:
        st.session_state["logado"] = False

    if not st.session_state["logado"]:

        tela_login()
        st.stop()


def logout():

    enviar_resumo_navegacao_telegram()

    st.session_state["logado"] = False
    st.session_state["usuario"] = None
    st.session_state["nome_usuario"] = None
    st.session_state["perfil_usuario"] = None
    st.session_state["auditoria_sessao_iniciada"] = False
    st.rerun()


exigir_login()


if not st.session_state.get("geo_solicitada_sessao", False):
    solicitar_localizacao_navegador()
    st.session_state["geo_solicitada_sessao"] = True


perfil_usuario = st.session_state.get(
    "perfil_usuario",
    "Consulta"
)

nome_usuario = st.session_state.get(
    "nome_usuario",
    ""
)

# Contexto Multiempresa
preparar_base_usuarios_multiempresa()

if "empresa_id_usuario" not in st.session_state:
    st.session_state["empresa_id_usuario"] = "1"

if "empresa_id_contexto" not in st.session_state:
    st.session_state["empresa_id_contexto"] = st.session_state.get("empresa_id_usuario", "1")

empresa_id_contexto = empresa_contexto_atual()
nome_empresa_contexto = obter_nome_empresa(empresa_id_contexto)

pode_exportar = perfil_usuario in [
    "Diretoria",
    "Pricing"
]

pode_ver_margem = perfil_usuario in [
    "Diretoria",
    "Pricing"
]

# Controle global de exportação por perfil
_st_download_button_original = st.download_button

def download_button_controlado(*args, **kwargs):

    if pode_exportar:
        return _st_download_button_original(*args, **kwargs)

    label = args[0] if len(args) > 0 else kwargs.get("label", "Download")

    return _st_download_button_original(
        label=f"{label} 🔒",
        data="Seu perfil não tem permissão para exportar.",
        file_name="sem_permissao.txt",
        mime="text/plain",
        disabled=True
    )

st.download_button = download_button_controlado




# --------------------------------------------------

st.markdown(
    """
    <style>
        .block-container {
            max-width: 100% !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
        }

        div[data-testid="stDataFrame"] {
            width: 100% !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

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
        width=460
    )

except:
    pass

st.markdown(
    """
    <div class="eirox-hero">
        <div class="eirox-section-title">Eirox Pricing Enterprise</div>
        <h1>📊 Inteligência de Pricing & Competitividade</h1>
        <p>Monitoramento executivo de preços, concorrência, margem, alertas e oportunidades comerciais.</p>
    </div>
    """,
    unsafe_allow_html=True
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

if historico.empty:
    historico = ler_base_pasta_ou_zip(
        ["VENDA_TESTE"],
        ["VENDA_TESTE.zip"]
    )

if compra.empty:
    compra = ler_base_pasta_ou_zip(
        ["COMPRA_TESTE", "COMPRA", "COMPRAS_TESTE"],
        ["COMPRA_TESTE.zip", "COMPRA.zip"]
    )

if venda_rede.empty:
    venda_rede = ler_base_pasta_ou_zip(
        ["VENDA_FINAL_TESTE", "VENDA_TESTE_FINAL", "VENDA_FINAL", "VENDA_REDE"],
        ["VENDA_FINAL_TESTE.zip", "VENDA_TESTE_FINAL.zip", "VENDA_FINAL.zip"]
    )

if estoque.empty:
    estoque = ler_base_pasta_ou_zip(
        ["ESTOQUE_TESTE", "ESTOQUE"],
        ["ESTOQUE_TESTE.zip", "ESTOQUE.zip"]
    )

# Fallback final compatível com .xls, .xlsx e .xlsm
# Necessário para Streamlit Cloud quando a pasta contém arquivos .xls.
if historico.empty:
    historico = carregar_pasta_excel_compat(
        ["VENDA_TESTE"],
        "VENDA_TESTE"
    )

if compra.empty:
    compra = carregar_pasta_excel_compat(
        ["COMPRA_TESTE", "COMPRA", "COMPRAS_TESTE"],
        "COMPRA_TESTE"
    )

if venda_rede.empty:
    venda_rede = carregar_pasta_excel_compat(
        ["VENDA_FINAL_TESTE", "VENDA_TESTE_FINAL", "VENDA_FINAL", "VENDA_REDE"],
        "VENDA_FINAL_TESTE"
    )

# Última tentativa: procurar a venda final em qualquer pasta do projeto
# identificando automaticamente arquivos com Cód. Barras/Etiq., Itens e Venda.
if venda_rede.empty:
    venda_rede = carregar_base_recursiva_por_colunas(
        "VENDA_FINAL_TESTE",
        [
            "Cód. Barras/Etiq.",
            "Itens",
            "Venda"
        ]
    )

if estoque.empty:
    estoque = carregar_pasta_excel_compat(
        ["ESTOQUE_TESTE", "ESTOQUE"],
        "ESTOQUE_TESTE"
    )

# Fallback robusto para Streamlit Cloud / GitHub
if historico.empty:
    historico = carregar_base_robusta(
        "VENDA_TESTE",
        ["VENDA_TESTE"],
        ["VENDA_TESTE.zip"]
    )

if compra.empty:
    compra = carregar_base_robusta(
        "COMPRA_TESTE",
        ["COMPRA_TESTE", "COMPRA", "COMPRAS_TESTE"],
        ["COMPRA_TESTE.zip", "COMPRA.zip"]
    )

if venda_rede.empty:
    venda_rede = carregar_base_robusta(
        "VENDA_FINAL_TESTE",
        ["VENDA_FINAL_TESTE", "VENDA_TESTE_FINAL", "VENDA_FINAL", "VENDA_REDE"],
        ["VENDA_FINAL_TESTE.zip", "VENDA_TESTE_FINAL.zip", "VENDA_FINAL.zip"]
    )

if estoque.empty:
    estoque = carregar_base_robusta(
        "ESTOQUE_TESTE",
        ["ESTOQUE_TESTE", "ESTOQUE"],
        ["ESTOQUE_TESTE.zip", "ESTOQUE.zip"]
    )

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
# GANHO POTENCIAL INTELIGENTE
# --------------------------------------------------

simulacao_global = pd.DataFrame()
origem_simulacao_global = "sem_calculo"

df, simulacao_global, origem_simulacao_global = recalcular_ganho_inteligente(
    df,
    venda_rede,
    historico
)

# Ganho potencial único para todas as visões e indicadores.
df = propagar_ganho_potencial(df)

if isinstance(simulacao_global, pd.DataFrame) and not simulacao_global.empty:

    if "Ganho_Potencial_Simulador" in simulacao_global.columns:

        simulacao_global["Ganho_Potencial"] = pd.to_numeric(
            simulacao_global["Ganho_Potencial_Simulador"],
            errors="coerce"
        ).fillna(0)

        simulacao_global["Ganho_Potencial_Atualizado"] = simulacao_global["Ganho_Potencial"]
        simulacao_global["Ganho_Potencial_Final"] = simulacao_global["Ganho_Potencial"]

# --------------------------------------------------
# MENU LATERAL / FILTROS
# --------------------------------------------------

try:

    st.sidebar.image(
        "logo eirox.png",
        width=280
    )

except Exception:

    pass

st.sidebar.markdown(
    """
    <div class="sidebar-card">
        <div class="sidebar-title">Eirox Pricing</div>
        <div class="sidebar-subtitle">Inteligência de preços e competitividade</div>
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown(
    f"""
    <div class="sidebar-card">
        <div class="sidebar-section" style="margin-top:0;">Usuário</div>
        <div class="sidebar-user"><b>{nome_usuario}</b></div>
        <div class="sidebar-pill">{perfil_usuario}</div>
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown(
    '<div class="sidebar-section">Navegação</div>',
    unsafe_allow_html=True
)

st.sidebar.caption(
    f"Enterprise {VERSAO_APP.split('-')[0]}"
)

# Seletor Multiempresa no local correto do menu lateral.
if usuario_master():
    empresas_ctx = carregar_empresas_sistema()
    empresas_ctx = empresas_ctx[
        empresas_ctx["Ativa"].astype(str).str.lower().eq("sim")
    ].copy()

    if not empresas_ctx.empty:
        mapa_empresas_ctx = {
            f'{row["EmpresaID"]} - {row["Empresa"]}': str(row["EmpresaID"])
            for _, row in empresas_ctx.iterrows()
        }

        empresa_atual_id = st.session_state.get(
            "empresa_id_contexto",
            st.session_state.get("empresa_id_usuario", "1")
        )

        labels_empresas = list(mapa_empresas_ctx.keys())
        index_empresa = 0

        for i, label in enumerate(labels_empresas):
            if mapa_empresas_ctx[label] == str(empresa_atual_id):
                index_empresa = i
                break

        empresa_label_sel = st.sidebar.selectbox(
            "🏢 Empresa em contexto",
            labels_empresas,
            index=index_empresa,
            key="select_empresa_contexto_master_menu"
        )

        st.session_state["empresa_id_contexto"] = mapa_empresas_ctx[empresa_label_sel]
        empresa_id_contexto = empresa_contexto_atual()
        nome_empresa_contexto = obter_nome_empresa(empresa_id_contexto)

st.sidebar.caption(
    f"Empresa: {nome_empresa_contexto}"
)


paginas_liberadas = PERMISSOES_TELAS.get(
    perfil_usuario,
    [
        "📊 Dashboard Geral",
        "🏢 Dashboard Executivo"
    ]
)

if usuario_pode_gerenciar_usuarios() and "👥 Controle de Usuários" not in paginas_liberadas:
    paginas_liberadas = paginas_liberadas + ["👥 Controle de Usuários"]

if usuario_pode_ver_auditoria() and "🟢 Saúde do Sistema" not in paginas_liberadas:
    paginas_liberadas = paginas_liberadas + ["🟢 Saúde do Sistema"]

if usuario_pode_ver_auditoria() and "📦 Backup Center" not in paginas_liberadas:
    paginas_liberadas = paginas_liberadas + ["📦 Backup Center"]

if usuario_pode_ver_multiempresa() and "🏢 Multiempresa" not in paginas_liberadas:
    paginas_liberadas = paginas_liberadas + ["🏢 Multiempresa"]

if usuario_pode_ver_multiempresa():
    for pagina_enterprise in [
        "📌 Sobre o Eirox",
        "🧭 Roadmap do Produto",
        "💼 Licenciamento Multiempresa",
        "💼 Licenciamento Real",
        "🚨 Alertas Inteligentes",
        "💰 Motor de Oportunidades"
    ]:
        if pagina_enterprise not in paginas_liberadas:
            paginas_liberadas = paginas_liberadas + [pagina_enterprise]

if usuario_pode_ver_auditoria() and "🔐 Central de Auditoria" not in paginas_liberadas:
    paginas_liberadas = paginas_liberadas + ["🔐 Central de Auditoria"]


if usuario_pode_ver_release_candidate() and "🏁 Release Candidate" not in paginas_liberadas:
    paginas_liberadas = paginas_liberadas + ["🏁 Release Candidate"]


if usuario_pode_ver_ia_pricing() and "🤖 IA Pricing Enterprise" not in paginas_liberadas:
    paginas_liberadas = paginas_liberadas + ["🤖 IA Pricing Enterprise"]


if usuario_pode_ver_workflow_comercial() and "📋 Workflow Comercial" not in paginas_liberadas:
    paginas_liberadas = paginas_liberadas + ["📋 Workflow Comercial"]


if usuario_pode_ver_crm_enterprise() and "🏢 CRM Enterprise" not in paginas_liberadas:
    paginas_liberadas = paginas_liberadas + ["🏢 CRM Enterprise"]


# Aplica plano e separa menu por área

if usuario_pode_ver_portal_cliente() and "🏢 Portal do Cliente" not in paginas_liberadas:
    paginas_liberadas = paginas_liberadas + ["🏢 Portal do Cliente"]


if usuario_pode_ver_billing_enterprise() and "💳 Billing Enterprise" not in paginas_liberadas:
    paginas_liberadas = paginas_liberadas + ["💳 Billing Enterprise"]

paginas_liberadas = filtrar_paginas_por_plano(paginas_liberadas)
paginas_cliente_menu, paginas_admin_menu = dividir_menu_cliente_admin(paginas_liberadas)

plano_atual_menu = plano_empresa_contexto()

st.sidebar.markdown(
    f"""
    <div class="sidebar-section">Área do Cliente</div>
    <div class="sidebar-user">Plano: <b>{plano_atual_menu}</b></div>
    """,
    unsafe_allow_html=True
)

pagina = None

if paginas_cliente_menu:
    pagina_cliente = st.sidebar.radio(
        "Cliente",
        paginas_cliente_menu,
        index=0,
        label_visibility="collapsed",
        key="menu_area_cliente"
    )
    pagina = pagina_cliente

if usuario_master() and paginas_admin_menu:
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        <div class="sidebar-section">Administração Eirox</div>
        """,
        unsafe_allow_html=True
    )

    pagina_admin = st.sidebar.radio(
        "Administração",
        ["Selecionar..."] + paginas_admin_menu,
        index=0,
        label_visibility="collapsed",
        key="menu_area_admin"
    )

    if pagina_admin != "Selecionar...":
        pagina = pagina_admin

if pagina is None:
    st.error("Nenhuma página disponível para o plano atual.")
    st.stop()




if pagina not in paginas_liberadas:
    pagina = paginas_liberadas[0]

registrar_pagina_acessada(pagina)

if st.session_state.get("ultima_pagina_logada") != pagina:
    salvar_log_acesso("Navegação", pagina, "Troca de tela")
    st.session_state["ultima_pagina_logada"] = pagina
# enviar_alerta_localizacao_capturada()  # desativado para melhorar velocidade entre telas
# enviar_resumo_periodico_navegacao()  # desativado para melhorar velocidade entre telas

st.sidebar.markdown("---")

if st.sidebar.button(
    "🚪 Sair do sistema",
    use_container_width=True
):

    logout()

if not pode_exportar:
    st.sidebar.info(
        "🔒 Exportação bloqueada para este perfil."
    )

if not pode_ver_margem:
    st.sidebar.info(
        "🔒 Margem e custo restritos para este perfil."
    )

st.sidebar.markdown(
    '<div class="sidebar-section">Filtros Globais</div>',
    unsafe_allow_html=True
)

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




# Garante que todas as telas após os filtros recebam o ganho atualizado.
df_filtrado = propagar_ganho_potencial(df_filtrado)




# Mantém a barra visual durante a renderização da tela.
# Ela desaparece suavemente via CSS, evitando tela parada sem feedback.



# --------------------------------------------------
# CONTROLE DE USUÁRIOS

# --------------------------------------------------
# RELEASE CANDIDATE

# --------------------------------------------------
# IA PRICING ENTERPRISE

# --------------------------------------------------
# WORKFLOW COMERCIAL

# --------------------------------------------------
# CRM ENTERPRISE

# --------------------------------------------------
# PORTAL DO CLIENTE

# --------------------------------------------------
# BILLING ENTERPRISE
# --------------------------------------------------

if pagina == "💳 Billing Enterprise":

    if not usuario_pode_ver_billing_enterprise():
        st.error("Acesso não autorizado.")
        st.stop()

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">SaaS Revenue Operations</div>
            <h1>💳 Billing Enterprise</h1>
            <p>Gestão de mensalidades, faturas, trial, upgrades, MRR, ARR e integração com licenciamento.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.caption("ⓘ Controle financeiro SaaS para cobrança, receita recorrente, status financeiro e bloqueio por inadimplência.")

    metricas = metricas_billing_enterprise()

    st.markdown("### 🧭 Painel Executivo Billing")

    b1, b2, b3, b4, b5, b6, b7 = st.columns(7)

    b1.metric("Faturas", metricas.get("Faturas", 0))
    b2.metric("Em aberto", metricas.get("EmAberto", 0))
    b3.metric("Pagas", metricas.get("Pagas", 0))
    b4.metric("Vencidas", metricas.get("Vencidas", 0))
    b5.metric("Trial", metricas.get("Trial", 0))
    b6.metric("MRR", f"R$ {_billing_numero_br(metricas.get('MRR', 0))}")
    b7.metric("ARR", f"R$ {_billing_numero_br(metricas.get('ARR', 0))}")

    aba_faturas, aba_cadastro, aba_receita, aba_planos, aba_integracao = st.tabs(
        [
            "📄 Faturas",
            "✍️ Nova/Editar Fatura",
            "📈 Receita",
            "📦 Planos",
            "🔐 Licenciamento"
        ]
    )

    with aba_faturas:

        st.markdown("### 📄 Faturas")

        billing = carregar_billing_eirox()

        if billing.empty:
            st.info("Nenhuma fatura cadastrada.")
        else:
            view = billing.copy()

            view["Dias_Vencimento"] = view["Data_Vencimento"].apply(_billing_dias_vencimento)
            view["Valor_Num"] = view["Valor_Mensal"].apply(_billing_parse_numero)

            filtro_status = st.multiselect(
                "Filtrar status",
                sorted(view["Status"].dropna().astype(str).unique().tolist())
            )

            filtro_plano = st.multiselect(
                "Filtrar plano",
                sorted(view["Plano"].dropna().astype(str).unique().tolist())
            )

            if filtro_status:
                view = view[view["Status"].astype(str).isin(filtro_status)]

            if filtro_plano:
                view = view[view["Plano"].astype(str).isin(filtro_plano)]

            st.dataframe(
                view,
                use_container_width=True,
                hide_index=True
            )

            csv_billing = view.to_csv(
                index=False,
                sep=";",
                encoding="utf-8-sig"
            )

            st.download_button(
                "📥 Exportar Billing CSV",
                data=csv_billing,
                file_name="billing_eirox.csv",
                mime="text/csv",
                use_container_width=True
            )

    with aba_cadastro:

        st.markdown("### ✍️ Nova / Editar Fatura")

        billing = carregar_billing_eirox()

        opcoes_fatura = ["Nova fatura"]

        if not billing.empty:
            opcoes_fatura += [
                f'{row["FaturaID"]} - {row["Cliente"]}'
                for _, row in billing.iterrows()
            ]

        fatura_sel = st.selectbox(
            "Selecionar fatura",
            opcoes_fatura,
            key="billing_fatura_sel"
        )

        dados = {}

        if fatura_sel != "Nova fatura":
            fid = fatura_sel.split(" - ")[0].strip()
            linha = billing[billing["FaturaID"].astype(str) == fid]
            if not linha.empty:
                dados = linha.iloc[0].to_dict()

        clientes = carregar_clientes_eirox() if "carregar_clientes_eirox" in globals() else pd.DataFrame()

        cliente_labels = []

        if isinstance(clientes, pd.DataFrame) and not clientes.empty:
            cliente_labels = [
                f'{row["EmpresaID"]} - {row["Cliente"]}'
                for _, row in clientes.iterrows()
            ]

        if not cliente_labels:
            cliente_labels = [
                "1 - Marabá - Cliente teste",
                "2 - Belém - Cliente teste"
            ]

        empresa_padrao = str(dados.get("EmpresaID", "1"))
        idx_cliente = 0

        for i, label in enumerate(cliente_labels):
            if label.split(" - ")[0].strip() == empresa_padrao:
                idx_cliente = i
                break

        with st.form("form_billing_enterprise"):

            f1, f2, f3 = st.columns(3)

            fatura_id = f1.text_input(
                "FaturaID",
                value=dados.get("FaturaID", gerar_id_fatura())
            )

            cliente_label = f2.selectbox(
                "Cliente",
                cliente_labels,
                index=idx_cliente
            )

            plano = f3.selectbox(
                "Plano",
                list(PLANOS_BILLING_EIROX.keys()),
                index=list(PLANOS_BILLING_EIROX.keys()).index(dados.get("Plano", "Starter")) if dados.get("Plano", "Starter") in PLANOS_BILLING_EIROX else 0
            )

            empresa_id = cliente_label.split(" - ")[0].strip()
            cliente_nome = cliente_label.split(" - ", 1)[1].strip() if " - " in cliente_label else cliente_label

            valor_sugerido = str(PLANOS_BILLING_EIROX.get(plano, {}).get("Mensalidade", 0))

            f4, f5, f6 = st.columns(3)

            valor_mensal = f4.text_input(
                "Valor mensal",
                value=dados.get("Valor_Mensal", valor_sugerido)
            )

            data_emissao = f5.text_input(
                "Data emissão",
                value=dados.get("Data_Emissao", datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y")),
                placeholder="dd/mm/aaaa"
            )

            data_vencimento = f6.text_input(
                "Data vencimento",
                value=dados.get("Data_Vencimento", ""),
                placeholder="dd/mm/aaaa"
            )

            f7, f8, f9 = st.columns(3)

            data_pagamento = f7.text_input(
                "Data pagamento",
                value=dados.get("Data_Pagamento", ""),
                placeholder="dd/mm/aaaa"
            )

            status = f8.selectbox(
                "Status",
                ["Em aberto", "Paga", "Vencida", "Trial", "Suspenso", "Cancelada", "Inadimplente"],
                index=["Em aberto", "Paga", "Vencida", "Trial", "Suspenso", "Cancelada", "Inadimplente"].index(dados.get("Status", "Em aberto")) if dados.get("Status", "Em aberto") in ["Em aberto", "Paga", "Vencida", "Trial", "Suspenso", "Cancelada", "Inadimplente"] else 0
            )

            ciclo = f9.selectbox(
                "Ciclo",
                ["Mensal", "Trimestral", "Semestral", "Anual"],
                index=["Mensal", "Trimestral", "Semestral", "Anual"].index(dados.get("Ciclo", "Mensal")) if dados.get("Ciclo", "Mensal") in ["Mensal", "Trimestral", "Semestral", "Anual"] else 0
            )

            forma_pagamento = st.text_input(
                "Forma pagamento",
                value=dados.get("Forma_Pagamento", "")
            )

            observacao = st.text_area(
                "Observação",
                value=dados.get("Observacao", "")
            )

            salvar_fatura = st.form_submit_button(
                "💾 Salvar fatura",
                use_container_width=True
            )

        if salvar_fatura:
            ok, msg = criar_ou_atualizar_fatura_eirox(
                fatura_id,
                empresa_id,
                cliente_nome,
                plano,
                valor_mensal,
                data_emissao,
                data_vencimento,
                data_pagamento,
                status,
                ciclo,
                forma_pagamento,
                observacao
            )

            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    with aba_receita:

        st.markdown("### 📈 Receita SaaS")

        plano_df = faturamento_por_plano()
        cliente_df = faturamento_por_cliente()

        r1, r2 = st.columns(2)

        if not plano_df.empty:
            fig_plano = px.bar(
                plano_df,
                x="Receita",
                y="Plano",
                orientation="h",
                title="Receita por plano"
            )

            fig_plano.update_layout(
                height=420,
                yaxis=dict(autorange="reversed")
            )

            r1.plotly_chart(
                fig_plano,
                use_container_width=True
            )

            st.markdown("### 📦 Receita por plano")
            st.dataframe(
                plano_df,
                use_container_width=True,
                hide_index=True
            )

        if not cliente_df.empty:
            fig_cliente = px.bar(
                cliente_df.head(15),
                x="Receita",
                y="Cliente",
                orientation="h",
                title="Receita por cliente"
            )

            fig_cliente.update_layout(
                height=420,
                yaxis=dict(autorange="reversed")
            )

            r2.plotly_chart(
                fig_cliente,
                use_container_width=True
            )

            st.markdown("### 🏢 Receita por cliente")
            st.dataframe(
                cliente_df,
                use_container_width=True,
                hide_index=True
            )

    with aba_planos:

        st.markdown("### 📦 Planos comerciais")

        planos_df = pd.DataFrame(
            [
                {
                    "Plano": plano,
                    "Mensalidade": dados["Mensalidade"],
                    "MaxUsuarios": dados["MaxUsuarios"],
                    "MaxLojas": dados["MaxLojas"],
                    "ARR": dados["Mensalidade"] * 12
                }
                for plano, dados in PLANOS_BILLING_EIROX.items()
            ]
        )

        st.dataframe(
            planos_df,
            use_container_width=True,
            hide_index=True
        )

        st.info(
            "Os valores são parâmetros comerciais internos e podem ser ajustados no dicionário PLANOS_BILLING_EIROX."
        )

    with aba_integracao:

        st.markdown("### 🔐 Integração Billing x Licenciamento")

        st.info(
            "Esta rotina atualiza a licença da empresa conforme o status financeiro da fatura selecionada."
        )

        billing = carregar_billing_eirox()

        if billing.empty:
            st.warning("Nenhuma fatura disponível.")
        else:
            opcoes = [
                f'{row["FaturaID"]} - {row["Cliente"]} - {row["Status"]}'
                for _, row in billing.iterrows()
            ]

            fatura_integracao = st.selectbox(
                "Selecionar fatura para sincronizar",
                opcoes,
                key="billing_sync_licenca"
            )

            fid = fatura_integracao.split(" - ")[0].strip()
            linha = billing[billing["FaturaID"].astype(str) == fid]

            if not linha.empty:
                dados = linha.iloc[0].to_dict()

                st.dataframe(
                    pd.DataFrame([dados]),
                    use_container_width=True,
                    hide_index=True
                )

                if st.button(
                    "🔄 Atualizar licença conforme billing",
                    use_container_width=True
                ):
                    ok, msg = atualizar_licenca_por_billing(
                        dados.get("EmpresaID", ""),
                        dados.get("Cliente", ""),
                        dados.get("Plano", ""),
                        dados.get("Status", "")
                    )

                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

    st.stop()



# --------------------------------------------------

if pagina == "🏢 Portal do Cliente":

    if not usuario_pode_ver_portal_cliente():
        st.error("Acesso não autorizado.")
        st.stop()

    dados_cliente = portal_dados_cliente()
    metricas_lic = portal_metricas_licenca()
    metricas_uso = portal_metricas_uso()

    licenca = metricas_lic.get("Licenca", {})
    status_lic = metricas_lic.get("Status", {})

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">Client Success Portal</div>
            <h1>🏢 Portal do Cliente</h1>
            <p>Informações da empresa, licença, consumo, utilização, suporte e novidades da plataforma Eirox.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.caption("ⓘ Área exclusiva para acompanhamento da empresa, plano contratado, uso da licença e suporte.")

    aba_empresa, aba_licenca, aba_uso, aba_conhecimento, aba_suporte, aba_novidades = st.tabs(
        [
            "🏢 Minha Empresa",
            "💳 Minha Licença",
            "📈 Uso da Plataforma",
            "📚 Conhecimento",
            "🎫 Suporte",
            "🔔 Novidades"
        ]
    )

    with aba_empresa:

        st.markdown("### 🏢 Minha Empresa")

        e1, e2, e3, e4 = st.columns(4)

        e1.metric("Empresa", dados_cliente.get("Cliente", dados_cliente.get("Empresa", "-")))
        e2.metric("Cidade/UF", f'{dados_cliente.get("Cidade", "-")} / {dados_cliente.get("UF", "-")}')
        e3.metric("Lojas", dados_cliente.get("Qtd_Lojas", metricas_lic.get("LojasUsadas", 0)))
        e4.metric("Status", dados_cliente.get("Status", status_lic.get("StatusOperacional", "-")))

        st.markdown("### 📋 Dados cadastrais")

        dados_view = pd.DataFrame(
            [
                {"Campo": "EmpresaID", "Informação": dados_cliente.get("EmpresaID", "")},
                {"Campo": "Cliente", "Informação": dados_cliente.get("Cliente", "")},
                {"Campo": "CNPJ", "Informação": dados_cliente.get("CNPJ", "")},
                {"Campo": "Cidade", "Informação": dados_cliente.get("Cidade", "")},
                {"Campo": "UF", "Informação": dados_cliente.get("UF", "")},
                {"Campo": "Data implantação", "Informação": dados_cliente.get("Data_Implantacao", "")},
                {"Campo": "Responsável comercial", "Informação": dados_cliente.get("Responsavel_Comercial", "")},
                {"Campo": "Observação", "Informação": dados_cliente.get("Observacao", "")}
            ]
        )

        st.dataframe(dados_view, use_container_width=True, hide_index=True)

    with aba_licenca:

        st.markdown("### 💳 Minha Licença")

        max_usuarios = int(metricas_lic.get("MaxUsuarios", 0) or 0)
        usuarios_usados = int(metricas_lic.get("UsuariosUsados", 0) or 0)
        max_lojas = int(metricas_lic.get("MaxLojas", 0) or 0)
        lojas_usadas = int(metricas_lic.get("LojasUsadas", 0) or 0)

        perc_usuarios = (usuarios_usados / max_usuarios * 100) if max_usuarios else 0
        perc_lojas = (lojas_usadas / max_lojas * 100) if max_lojas else 0

        l1, l2, l3, l4, l5 = st.columns(5)

        l1.metric("Plano", licenca.get("Plano", dados_cliente.get("Plano", "-")))
        l2.metric("Status", status_lic.get("StatusOperacional", "-"))
        l3.metric("Dias restantes", status_lic.get("DiasRestantes", "-"))
        l4.metric("Usuários", f"{usuarios_usados} / {max_usuarios}")
        l5.metric("Lojas", f"{lojas_usadas} / {max_lojas}")

        st.markdown("### 📊 Consumo da licença")

        consumo = pd.DataFrame(
            [
                {"Recurso": "Usuários", "Utilizado": usuarios_usados, "Limite": max_usuarios, "Consumo": _portal_barra_consumo(perc_usuarios)},
                {"Recurso": "Lojas", "Utilizado": lojas_usadas, "Limite": max_lojas, "Consumo": _portal_barra_consumo(perc_lojas)}
            ]
        )

        st.dataframe(consumo, use_container_width=True, hide_index=True)

        st.info(f"Data de renovação cadastrada: {dados_cliente.get('Data_Renovacao', licenca.get('DataExpiracao', '-'))}")

    with aba_uso:

        st.markdown("### 📈 Utilização da Plataforma")

        u1, u2, u3, u4, u5 = st.columns(5)

        u1.metric("Último acesso", metricas_uso.get("UltimoAcesso", "-"))
        u2.metric("Usuários ativos", metricas_uso.get("UsuariosAtivos", 0))
        u3.metric("Total de acessos", metricas_uso.get("TotalAcessos", 0))
        u4.metric("Produtos monitorados", metricas_uso.get("ProdutosMonitorados", 0))
        u5.metric("Recomendações IA", metricas_uso.get("RecomendacoesIA", 0))

        atividade = pd.DataFrame(
            [
                {"Indicador": "Alertas gerados", "Valor": metricas_uso.get("Alertas", 0)},
                {"Indicador": "Produtos monitorados", "Valor": metricas_uso.get("ProdutosMonitorados", 0)},
                {"Indicador": "Recomendações IA", "Valor": metricas_uso.get("RecomendacoesIA", 0)},
                {"Indicador": "Total de acessos", "Valor": metricas_uso.get("TotalAcessos", 0)}
            ]
        )

        st.dataframe(atividade, use_container_width=True, hide_index=True)

    with aba_conhecimento:

        st.markdown("### 📚 Central de Conhecimento")

        materiais = pd.DataFrame(
            [
                {"Material": "Manual do Usuário", "Tipo": "PDF", "Status": "Disponível em breve", "Descrição": "Guia operacional da plataforma."},
                {"Material": "Manual Executivo", "Tipo": "PDF", "Status": "Disponível em breve", "Descrição": "Visão gerencial para diretores e gestores."},
                {"Material": "Guia IA Pricing", "Tipo": "PDF", "Status": "Disponível em breve", "Descrição": "Como interpretar recomendações da IA."},
                {"Material": "Roadmap Público", "Tipo": "Página", "Status": "Disponível", "Descrição": "Evolução planejada da plataforma."},
                {"Material": "Treinamento Comercial", "Tipo": "Vídeo", "Status": "Disponível em breve", "Descrição": "Capacitação para uso comercial."}
            ]
        )

        st.dataframe(materiais, use_container_width=True, hide_index=True)

        st.info("Os arquivos físicos dos manuais poderão ser adicionados em uma próxima etapa na pasta DOCUMENTOS_EIROX.")

    with aba_suporte:

        st.markdown("### 🎫 Central de Suporte")

        with st.form("form_suporte_cliente"):

            assunto = st.text_input("Assunto", placeholder="Ex.: Dúvida sobre IA Pricing")
            prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta", "Crítica"])
            mensagem = st.text_area("Mensagem", placeholder="Descreva sua dúvida ou solicitação.")

            abrir = st.form_submit_button("🎫 Abrir chamado", use_container_width=True)

        if abrir:
            if not assunto.strip() or not mensagem.strip():
                st.error("Assunto e mensagem são obrigatórios.")
            else:
                ok, msg = salvar_chamado_suporte_cliente(assunto, prioridade, mensagem)

                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        st.markdown("### 📜 Histórico de chamados")

        chamados = carregar_chamados_suporte_cliente()

        empresa_id, _ = portal_empresa_atual()

        if not chamados.empty and "EmpresaID" in chamados.columns:
            chamados = chamados[chamados["EmpresaID"].astype(str).str.strip() == str(empresa_id)]

        if chamados.empty:
            st.info("Nenhum chamado aberto para esta empresa.")
        else:
            st.dataframe(chamados.tail(100), use_container_width=True, hide_index=True)

    with aba_novidades:

        st.markdown("### 🔔 Novidades da Plataforma")

        novidades = portal_novidades()

        st.dataframe(novidades, use_container_width=True, hide_index=True)

        st.markdown("### 🚀 Próxima evolução")

        st.info("A próxima etapa sugerida é a v1.40.0 Billing Enterprise, com faturas, mensalidades, renovação, upgrades de plano e controle financeiro.")

    st.stop()



# --------------------------------------------------

if pagina == "🏢 CRM Enterprise":

    if not usuario_pode_ver_crm_enterprise():
        st.error("Acesso não autorizado.")
        st.stop()

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">Customer Revenue Management</div>
            <h1>🏢 CRM Enterprise</h1>
            <p>Gestão comercial de clientes, planos, implantação, receita recorrente e renovação de licenças.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.caption("ⓘ Cadastro e acompanhamento comercial dos clientes SaaS da plataforma Eirox.")

    metricas = metricas_crm_enterprise()

    st.markdown("### 🧭 Painel Executivo de Clientes")

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.metric("Clientes", metricas.get("Clientes", 0))
    c2.metric("Ativos", metricas.get("Ativos", 0))
    c3.metric("Implantação", metricas.get("Implantacao", 0))
    c4.metric("Suspensos", metricas.get("Suspensos", 0))
    c5.metric("Lojas", metricas.get("Lojas", 0))
    c6.metric("MRR", f"R$ {_crm_numero_br(metricas.get('MRR', 0))}")

    clientes = carregar_clientes_eirox()

    aba_cadastro, aba_base, aba_dashboard = st.tabs(
        [
            "✍️ Cadastro",
            "📋 Base de Clientes",
            "📊 Dashboard Comercial"
        ]
    )

    with aba_cadastro:

        st.markdown("### ✍️ Cadastro / Atualização de Cliente")

        opcoes = ["Novo cliente"]

        if not clientes.empty:
            opcoes += [
                f'{row["ClienteID"]} - {row["Cliente"]}'
                for _, row in clientes.iterrows()
            ]

        cliente_sel = st.selectbox(
            "Selecionar cliente",
            opcoes,
            key="crm_cliente_sel"
        )

        dados = {}

        if cliente_sel != "Novo cliente":
            cliente_id_sel = cliente_sel.split(" - ")[0].strip()
            linha = clientes[clientes["ClienteID"].astype(str) == cliente_id_sel]
            if not linha.empty:
                dados = linha.iloc[0].to_dict()

        with st.form("form_crm_enterprise"):

            f1, f2, f3 = st.columns(3)

            cliente_id = f1.text_input(
                "ClienteID",
                value=dados.get("ClienteID", "")
            )

            empresa_id = f2.text_input(
                "EmpresaID",
                value=dados.get("EmpresaID", "")
            )

            cliente_nome = f3.text_input(
                "Cliente",
                value=dados.get("Cliente", "")
            )

            f4, f5, f6 = st.columns(3)

            cnpj = f4.text_input(
                "CNPJ",
                value=dados.get("CNPJ", "")
            )

            cidade = f5.text_input(
                "Cidade",
                value=dados.get("Cidade", "")
            )

            uf = f6.text_input(
                "UF",
                value=dados.get("UF", "")
            )

            f7, f8, f9 = st.columns(3)

            qtd_lojas = f7.text_input(
                "Quantidade de lojas",
                value=dados.get("Qtd_Lojas", "0")
            )

            plano = f8.selectbox(
                "Plano",
                ["Starter", "Professional", "Enterprise", "Enterprise Plus"],
                index=["Starter", "Professional", "Enterprise", "Enterprise Plus"].index(dados.get("Plano", "Starter")) if dados.get("Plano", "Starter") in ["Starter", "Professional", "Enterprise", "Enterprise Plus"] else 0
            )

            mrr = f9.text_input(
                "MRR mensal",
                value=dados.get("MRR", "0")
            )

            f10, f11, f12 = st.columns(3)

            data_implantacao = f10.text_input(
                "Data implantação",
                value=dados.get("Data_Implantacao", ""),
                placeholder="dd/mm/aaaa"
            )

            data_renovacao = f11.text_input(
                "Data renovação",
                value=dados.get("Data_Renovacao", ""),
                placeholder="dd/mm/aaaa"
            )

            status = f12.selectbox(
                "Status",
                ["Implantação", "Ativo", "Suspenso", "Cancelado", "Trial"],
                index=["Implantação", "Ativo", "Suspenso", "Cancelado", "Trial"].index(dados.get("Status", "Implantação")) if dados.get("Status", "Implantação") in ["Implantação", "Ativo", "Suspenso", "Cancelado", "Trial"] else 0
            )

            responsavel = st.text_input(
                "Responsável comercial",
                value=dados.get("Responsavel_Comercial", "")
            )

            observacao = st.text_area(
                "Observação",
                value=dados.get("Observacao", "")
            )

            salvar = st.form_submit_button(
                "💾 Salvar cliente",
                use_container_width=True
            )

        if salvar:
            ok, msg = criar_ou_atualizar_cliente_eirox(
                cliente_id,
                empresa_id,
                cliente_nome,
                cnpj,
                cidade,
                uf,
                qtd_lojas,
                plano,
                mrr,
                data_implantacao,
                data_renovacao,
                status,
                responsavel,
                observacao
            )

            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    with aba_base:

        st.markdown("### 📋 Base de Clientes")

        if clientes.empty:
            st.info("Nenhum cliente cadastrado.")
        else:
            filtro_status = st.multiselect(
                "Filtrar status",
                sorted(clientes["Status"].dropna().astype(str).unique().tolist())
            )

            filtro_plano = st.multiselect(
                "Filtrar plano",
                sorted(clientes["Plano"].dropna().astype(str).unique().tolist())
            )

            view = clientes.copy()

            if filtro_status:
                view = view[view["Status"].astype(str).isin(filtro_status)]

            if filtro_plano:
                view = view[view["Plano"].astype(str).isin(filtro_plano)]

            st.dataframe(
                view,
                use_container_width=True,
                hide_index=True
            )

            csv_clientes = view.to_csv(
                index=False,
                sep=";",
                encoding="utf-8-sig"
            )

            st.download_button(
                "📥 Exportar Clientes CSV",
                data=csv_clientes,
                file_name="clientes_eirox.csv",
                mime="text/csv",
                use_container_width=True
            )

    with aba_dashboard:

        st.markdown("### 📊 Dashboard Comercial")

        if clientes.empty:
            st.info("Nenhum cliente cadastrado para análise.")
        else:
            dash = clientes.copy()

            dash["MRR_Num"] = pd.to_numeric(
                dash["MRR"].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
                errors="coerce"
            ).fillna(0)

            dash["Qtd_Lojas_Num"] = pd.to_numeric(
                dash["Qtd_Lojas"],
                errors="coerce"
            ).fillna(0)

            d1, d2 = st.columns(2)

            status_df = (
                dash
                .groupby("Status", dropna=False)
                .size()
                .reset_index(name="Clientes")
            )

            fig_status = px.bar(
                status_df,
                x="Status",
                y="Clientes",
                title="Clientes por status"
            )

            fig_status.update_layout(height=380)

            d1.plotly_chart(
                fig_status,
                use_container_width=True
            )

            plano_df = (
                dash
                .groupby("Plano", dropna=False)
                .agg(
                    MRR=("MRR_Num", "sum"),
                    Clientes=("Cliente", "count"),
                    Lojas=("Qtd_Lojas_Num", "sum")
                )
                .reset_index()
                .sort_values("MRR", ascending=False)
            )

            fig_plano = px.bar(
                plano_df,
                x="MRR",
                y="Plano",
                orientation="h",
                title="MRR por plano"
            )

            fig_plano.update_layout(
                height=380,
                yaxis=dict(autorange="reversed")
            )

            d2.plotly_chart(
                fig_plano,
                use_container_width=True
            )

            st.markdown("### 💰 Receita por plano")

            st.dataframe(
                plano_df,
                use_container_width=True,
                hide_index=True
            )

    st.stop()



# --------------------------------------------------

if pagina == "📋 Workflow Comercial":

    if not usuario_pode_ver_workflow_comercial():
        st.error("Acesso não autorizado.")
        st.stop()

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">Commercial Approval Flow</div>
            <h1>📋 Workflow Comercial</h1>
            <p>Fluxo de aprovação, rejeição e auditoria das recomendações comerciais geradas pela IA Pricing.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.caption("ⓘ Fluxo de aprovação, rejeição e auditoria das recomendações comerciais da IA Pricing.")

    workflow = carregar_workflow_comercial()

    pendentes = int((workflow["Status"].astype(str) == "Pendente").sum()) if not workflow.empty and "Status" in workflow.columns else 0
    analise = int((workflow["Status"].astype(str) == "Em análise").sum()) if not workflow.empty and "Status" in workflow.columns else 0
    aprovados = int((workflow["Status"].astype(str) == "Aprovado").sum()) if not workflow.empty and "Status" in workflow.columns else 0
    rejeitados = int((workflow["Status"].astype(str) == "Rejeitado").sum()) if not workflow.empty and "Status" in workflow.columns else 0

    st.markdown("### 🧭 Painel Executivo do Workflow")

    w1, w2, w3, w4, w5 = st.columns(5)
    w1.metric("Pendentes", pendentes)
    w2.metric("Em análise", analise)
    w3.metric("Aprovadas", aprovados)
    w4.metric("Rejeitadas", rejeitados)
    w5.metric("Total", len(workflow))

    st.markdown("### ➕ Enviar recomendações para aprovação")

    col_add1, col_add2 = st.columns(2)

    if col_add1.button("🤖 Importar recomendações da IA Pricing", use_container_width=True):
        ia_df = st.session_state.get("ia_pricing_df", pd.DataFrame())
        if ia_df.empty:
            st.info("Nenhuma recomendação da IA Pricing encontrada na sessão. Gere primeiro na tela IA Pricing Enterprise.")
        else:
            ok, msg = adicionar_recomendacoes_ao_workflow(ia_df, origem="IA Pricing")
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.warning(msg)

    if col_add2.button("💰 Importar Motor de Oportunidades", use_container_width=True):
        op_df = st.session_state.get("motor_oportunidades_df", pd.DataFrame())
        if op_df.empty:
            st.info("Nenhuma oportunidade encontrada na sessão. Gere primeiro na tela Motor de Oportunidades.")
        else:
            ok, msg = adicionar_recomendacoes_ao_workflow(op_df, origem="Motor de Oportunidades")
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.warning(msg)

    st.markdown("### 🔎 Recomendações em workflow")

    if workflow.empty:
        st.info("Nenhuma recomendação no workflow comercial.")
        st.stop()

    view = workflow.copy()

    filtro_status = st.multiselect(
        "Filtrar status",
        sorted(view["Status"].dropna().astype(str).unique().tolist()) if "Status" in view.columns else []
    )

    filtro_origem = st.multiselect(
        "Filtrar origem",
        sorted(view["Origem"].dropna().astype(str).unique().tolist()) if "Origem" in view.columns else []
    )

    if filtro_status and "Status" in view.columns:
        view = view[view["Status"].astype(str).isin(filtro_status)]

    if filtro_origem and "Origem" in view.columns:
        view = view[view["Origem"].astype(str).isin(filtro_origem)]

    st.dataframe(view, use_container_width=True, hide_index=True)

    st.markdown("### ✅ Aprovação / Rejeição")

    ids_disponiveis = view["ID"].dropna().astype(str).tolist() if "ID" in view.columns else []

    ids_sel = st.multiselect(
        "Selecionar recomendações",
        ids_disponiveis
    )

    novo_status = st.selectbox(
        "Novo status",
        ["Em análise", "Aprovado", "Rejeitado", "Pendente"]
    )

    justificativa = st.text_area(
        "Justificativa",
        placeholder="Informe o motivo da aprovação, rejeição ou alteração de status."
    )

    if st.button("💾 Atualizar status selecionado", use_container_width=True):
        ok, msg = atualizar_status_workflow(ids_sel, novo_status, justificativa)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    st.markdown("### 📤 Exportação")

    csv_workflow = view.to_csv(index=False, sep=";", encoding="utf-8-sig")

    st.download_button(
        "📥 Exportar Workflow CSV",
        data=csv_workflow,
        file_name="workflow_comercial_eirox.csv",
        mime="text/csv",
        use_container_width=True
    )

    st.stop()



# --------------------------------------------------

if pagina == "🤖 IA Pricing Enterprise":

    if not usuario_pode_ver_ia_pricing():
        st.error("Acesso não autorizado.")
        st.stop()

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">AI Pricing Decision Engine</div>
            <h1>🤖 IA Pricing Enterprise</h1>
            <p>Recomendações automáticas de preço com base em margem, concorrência, custo, estoque e oportunidade financeira.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    if "legenda_tela" in globals():
        legenda_tela("🤖 IA Pricing Enterprise")

    st.markdown("### ⚙️ Parâmetros da IA")
    p1, p2, p3, p4, p5 = st.columns(5)
    margem_minima = p1.number_input("Margem mínima (%)", min_value=0, max_value=100, value=25, step=1)
    margem_alvo = p2.number_input("Margem alvo (%)", min_value=1, max_value=90, value=35, step=1)
    limite_reducao = p3.number_input("Limite redução (%)", min_value=0, max_value=50, value=8, step=1)
    limite_aumento = p4.number_input("Limite aumento (%)", min_value=0, max_value=50, value=12, step=1)
    top_n = p5.number_input("Top recomendações", min_value=10, max_value=1000, value=150, step=10)

    col_gerar, col_enviar = st.columns(2)
    if "ia_pricing_df" not in st.session_state:
        st.session_state["ia_pricing_df"] = pd.DataFrame()

    if col_gerar.button("🤖 Gerar Recomendações IA", use_container_width=True):
        with st.spinner("IA Pricing analisando margem, custo, estoque e concorrência..."):
            ia_df = gerar_ia_pricing_enterprise(margem_minima, margem_alvo, limite_reducao, limite_aumento, top_n)
        st.session_state["ia_pricing_df"] = ia_df
        if ia_df.empty:
            st.info("Nenhuma recomendação encontrada com os parâmetros atuais.")
        else:
            salvar_recomendacoes_ia(ia_df)
            st.success(f"🤖 {len(ia_df)} recomendações geradas pela IA Pricing.")

    ia_df = st.session_state.get("ia_pricing_df", pd.DataFrame())

    if col_enviar.button("📨 Enviar Top 10 ao Telegram", use_container_width=True):
        if ia_df.empty:
            st.info("Gere as recomendações antes de enviar.")
        else:
            ok, msg = enviar_ia_pricing_telegram(ia_df, limite_envio=10)
            st.success(msg) if ok else st.error(msg)

    if not ia_df.empty:
        ganho_total = ia_df["Ganho_Estimado"].sum() if "Ganho_Estimado" in ia_df.columns else 0
        aumentar = int((ia_df["Ação"].astype(str) == "Aumentar preço").sum()) if "Ação" in ia_df.columns else 0
        reduzir = int((ia_df["Ação"].astype(str) == "Reduzir preço").sum()) if "Ação" in ia_df.columns else 0
        manter = int((ia_df["Ação"].astype(str) == "Manter").sum()) if "Ação" in ia_df.columns else 0

        st.markdown("### 🧭 Painel Executivo IA")
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Ganho estimado", f"R$ {_ia_numero_br(ganho_total)}")
        k2.metric("Aumentar preço", aumentar)
        k3.metric("Reduzir preço", reduzir)
        k4.metric("Manter", manter)
        k5.metric("Recomendações", len(ia_df))

        st.markdown("### 🎯 Recomendações automáticas")
        view = ia_df.copy()
        filtro_acao = st.multiselect("Filtrar ação", sorted(view["Ação"].dropna().astype(str).unique().tolist()) if "Ação" in view.columns else [])
        filtro_curva = st.multiselect("Filtrar curva", sorted(view["Curva"].dropna().astype(str).unique().tolist()) if "Curva" in view.columns else [])
        if filtro_acao and "Ação" in view.columns:
            view = view[view["Ação"].astype(str).isin(filtro_acao)]
        if filtro_curva and "Curva" in view.columns:
            view = view[view["Curva"].astype(str).isin(filtro_curva)]
        st.dataframe(view, use_container_width=True, hide_index=True)

        st.markdown("### 📊 Distribuição de recomendações")
        c1, c2 = st.columns(2)
        if "Ação" in ia_df.columns:
            dist = ia_df.groupby("Ação", dropna=False).size().reset_index(name="Quantidade")
            fig_dist = px.bar(dist, x="Ação", y="Quantidade", title="Recomendações por ação")
            fig_dist.update_layout(height=360, margin=dict(l=10, r=10, t=60, b=10))
            c1.plotly_chart(fig_dist, use_container_width=True)
        if "Laboratório" in ia_df.columns:
            ganho_lab = ia_df.groupby("Laboratório", dropna=False).agg(Ganho_Estimado=("Ganho_Estimado", "sum")).reset_index().sort_values("Ganho_Estimado", ascending=False).head(15)
            fig_lab = px.bar(ganho_lab, x="Ganho_Estimado", y="Laboratório", orientation="h", title="Ganho estimado por laboratório")
            fig_lab.update_layout(height=420, margin=dict(l=10, r=10, t=60, b=10), yaxis=dict(autorange="reversed"))
            c2.plotly_chart(fig_lab, use_container_width=True)

        csv_ia = view.to_csv(index=False, sep=";", encoding="utf-8-sig")
        st.download_button("📥 Exportar Recomendações IA CSV", data=csv_ia, file_name="ia_pricing_enterprise_eirox.csv", mime="text/csv", use_container_width=True)

    st.markdown("### 📜 Histórico IA Pricing")
    hist_ia = carregar_historico_ia_pricing()
    if hist_ia.empty:
        st.info("Nenhum histórico registrado ainda.")
    else:
        st.dataframe(hist_ia.tail(300), use_container_width=True, hide_index=True)

    st.stop()


# --------------------------------------------------

if pagina == "🏁 Release Candidate":

    if not usuario_pode_ver_release_candidate():
        st.error("Acesso não autorizado.")
        st.stop()

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">Release Governance</div>
            <h1>🏁 Release Candidate</h1>
            <p>Checklist de estabilização, prontidão comercial, arquivos críticos e preparação para produção.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    if "legenda_tela" in globals():
        legenda_tela("🏁 Release Candidate")

    resumo_rc = gerar_resumo_release_candidate()

    st.markdown("### 🧭 Status Executivo da RC")

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Status", resumo_rc.get("Status", "-"))
    r2.metric("Checks OK", f'{resumo_rc.get("ChecksOK", 0)} / {resumo_rc.get("TotalChecks", 0)}')
    r3.metric("Arquivos OK", f'{resumo_rc.get("ArquivosOK", 0)} / {resumo_rc.get("TotalArquivos", 0)}')
    r4.metric("Versão", f"Enterprise {VERSAO_APP.split('-')[0]}")

    st.markdown("### ✅ Checklist de Prontidão")
    checklist = gerar_checklist_rc()
    st.dataframe(checklist, use_container_width=True, hide_index=True)

    st.markdown("### 📁 Arquivos Administrativos Críticos")
    arquivos_rc = gerar_status_arquivos_rc()
    st.dataframe(arquivos_rc, use_container_width=True, hide_index=True)

    st.markdown("### 🧩 Política de Release")
    politica = pd.DataFrame(
        [
            {"Regra": "Produção congelada", "Descrição": "v1.34.0 permanece como base de produção estável."},
            {"Regra": "Homologação RC", "Descrição": "v1.36.3 RC concentra recursos comerciais antes da versão final."},
            {"Regra": "Acesso master", "Descrição": "Módulos administrativos permanecem restritos ao usuário paulomarques."},
            {"Regra": "Backup obrigatório", "Descrição": "Gerar backup completo antes de promover qualquer versão."},
            {"Regra": "Teste de cliente", "Descrição": "Validar login, menus, dados, backup, alertas e licenciamento antes de venda piloto."},
            {"Regra": "Rollback", "Descrição": "Manter backup e arquivo anterior para retorno imediato em caso de erro."}
        ]
    )
    st.dataframe(politica, use_container_width=True, hide_index=True)

    st.markdown("### 📤 Exportação da RC")
    checklist_export = checklist.copy()
    checklist_export["Grupo"] = "Checklist"
    arquivos_export = arquivos_rc.rename(columns={"Arquivo": "Item", "Última Atualização": "Detalhe"}).copy()
    arquivos_export["Grupo"] = "Arquivos"

    for col in ["Item", "Status", "Detalhe"]:
        if col not in arquivos_export.columns:
            arquivos_export[col] = ""

    rc_export = pd.concat(
        [
            checklist_export[["Grupo", "Item", "Status", "Detalhe"]],
            arquivos_export[["Grupo", "Item", "Status", "Detalhe"]]
        ],
        ignore_index=True
    )

    csv_rc = rc_export.to_csv(index=False, sep=";", encoding="utf-8-sig")

    st.download_button(
        "📥 Exportar Checklist RC",
        data=csv_rc,
        file_name="release_candidate_eirox_v1363.csv",
        mime="text/csv",
        use_container_width=True
    )

    st.info("Após validar esta RC, gere um backup completo e congele a v1.36.3 como candidata comercial.")

    st.stop()



# --------------------------------------------------

if pagina == "👥 Controle de Usuários":

    if not usuario_pode_gerenciar_usuarios():
        st.error("Acesso não autorizado.")
        st.stop()

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">Governança e Segurança</div>
            <h1>👥 Controle de Usuários</h1>
            <p>Cadastro, bloqueio, reset de senha, expiração de acesso e log de alterações.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    base_usuarios = carregar_usuarios_sistema()

    k1, k2, k3, k4 = st.columns(4)

    total_usuarios = len(base_usuarios)
    ativos = int((base_usuarios["Ativo"].astype(str).str.lower() == "sim").sum())
    bloqueados = total_usuarios - ativos
    expirados = int(base_usuarios["Expira_Em"].apply(usuario_expirado).sum())

    k1.metric("Usuários", total_usuarios)
    k2.metric("Ativos", ativos)
    k3.metric("Bloqueados", bloqueados)
    k4.metric("Expirados", expirados)

    aba1, aba2, aba3, aba4 = st.tabs(
        [
            "➕ Cadastro / Edição",
            "🔒 Bloqueio",
            "🔑 Reset de Senha",
            "📋 Logs"
        ]
    )

    with aba1:

        st.markdown("### ➕ Criar ou editar usuário")

        usuarios_existentes = ["Novo usuário"] + sorted(
            base_usuarios["Usuario"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        usuario_sel = st.selectbox(
            "Selecionar usuário",
            usuarios_existentes,
            key="controle_usuario_sel"
        )

        if usuario_sel != "Novo usuário":
            dados = (
                base_usuarios[
                    base_usuarios["Usuario"] == usuario_sel
                ]
                .iloc[0]
                .to_dict()
            )
        else:
            dados = {}

        with st.form("form_usuario_cadastro"):

            usuario_form = st.text_input(
                "Usuário",
                value=dados.get("Usuario", "") if dados else ""
            )

            nome_form = st.text_input(
                "Nome",
                value=dados.get("Nome", "") if dados else ""
            )

            perfis = [
                "Diretoria",
                "Pricing",
                "Comercial",
                "Regional",
                "Consulta"
            ]

            perfil_atual = dados.get("Perfil", "Consulta") if dados else "Consulta"

            perfil_form = st.selectbox(
                "Perfil",
                perfis,
                index=perfis.index(perfil_atual) if perfil_atual in perfis else 4
            )

            ativo_form = st.selectbox(
                "Ativo",
                ["Sim", "Não"],
                index=0 if dados.get("Ativo", "Sim") == "Sim" else 1
            )

            expira_form = st.text_input(
                "Expira em",
                value=dados.get("Expira_Em", "") if dados else "",
                placeholder="dd/mm/aaaa ou deixe vazio"
            )

            reset_form = st.selectbox(
                "Forçar reset de senha",
                ["Não", "Sim"],
                index=0 if dados.get("Forcar_Reset", "Não") == "Não" else 1
            )

            senha_form = st.text_input(
                "Senha",
                type="password",
                help="Obrigatória para novo usuário. Para editar, preencha apenas se quiser alterar a senha."
            )

            salvar = st.form_submit_button(
                "💾 Salvar usuário",
                use_container_width=True
            )

        if salvar:

            ok, msg = criar_ou_atualizar_usuario(
                usuario_form,
                nome_form,
                perfil_form,
                senha=senha_form if senha_form else None,
                ativo=ativo_form,
                expira_em=expira_form,
                forcar_reset=reset_form
            )

            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

        st.markdown("### 👥 Usuários cadastrados")

        usuarios_view = base_usuarios.copy()

        if "Senha_Hash" in usuarios_view.columns:
            usuarios_view["Senha_Hash"] = "********"

        st.dataframe(
            usuarios_view,
            use_container_width=True,
            hide_index=True
        )

    with aba2:

        st.markdown("### 🔒 Bloquear ou desbloquear usuário")

        usuario_status = st.selectbox(
            "Usuário",
            sorted(
                base_usuarios["Usuario"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            ),
            key="usuario_bloqueio"
        )

        colb1, colb2 = st.columns(2)

        if colb1.button("🔒 Bloquear", use_container_width=True):
            ok, msg = bloquear_desbloquear_usuario(
                usuario_status,
                False
            )

            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

        if colb2.button("🔓 Desbloquear", use_container_width=True):
            ok, msg = bloquear_desbloquear_usuario(
                usuario_status,
                True
            )

            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    with aba3:

        st.markdown("### 🔑 Reset de senha")

        usuario_reset = st.selectbox(
            "Usuário",
            sorted(
                base_usuarios["Usuario"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            ),
            key="usuario_reset_senha"
        )

        with st.form("form_reset_senha"):

            nova_senha = st.text_input(
                "Nova senha",
                type="password"
            )

            forcar_reset = st.selectbox(
                "Forçar reset no próximo acesso",
                ["Não", "Sim"],
                index=0
            )

            resetar = st.form_submit_button(
                "🔑 Resetar senha",
                use_container_width=True
            )

        if resetar:
            ok, msg = resetar_senha_usuario(
                usuario_reset,
                nova_senha,
                forcar_reset=forcar_reset
            )

            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    with aba4:

        st.markdown("### 📋 Log de alterações")

        logs_usuarios = carregar_log_usuarios()

        if logs_usuarios.empty:
            st.info("Ainda não existem logs de alterações de usuários.")
        else:
            st.dataframe(
                logs_usuarios,
                use_container_width=True,
                hide_index=True
            )

            csv_logs = logs_usuarios.to_csv(
                index=False,
                sep=";",
                encoding="utf-8-sig"
            )

            st.download_button(
                "📥 Exportar logs de usuários",
                data=csv_logs,
                file_name="logs_usuarios_eirox.csv",
                mime="text/csv",
                use_container_width=True
            )

    st.stop()







# --------------------------------------------------
# SOBRE O EIROX ENTERPRISE
# --------------------------------------------------

if pagina == "📌 Sobre o Eirox":

    if not usuario_pode_ver_multiempresa():
        st.error("Acesso não autorizado.")
        st.stop()

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">Eirox Pricing Enterprise</div>
            <h1>📌 Sobre o Eirox Enterprise</h1>
            <p>Plataforma de inteligência de pricing, competitividade e governança para redes de farmácia.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    legenda_tela("📌 Sobre o Eirox")

    c1, c2, c3 = st.columns(3)

    c1.metric("Categoria", "Pricing SaaS")
    c2.metric("Versão", f"Enterprise {VERSAO_APP.split('-')[0]}")
    c3.metric("Status", "Homologação avançada")

    card_enterprise(
        "Propósito",
        "Centralizar informações de concorrência, margem, compras, estoque, simulação e auditoria para apoiar decisões comerciais de alta precisão.",
        "🎯"
    )

    card_enterprise(
        "Principais diferenciais",
        "Auditoria completa, controle de usuários, saúde do sistema, backup, multiempresa e inteligência competitiva em uma única plataforma.",
        "🚀"
    )

    card_enterprise(
        "Governança",
        "Módulos administrativos restritos ao usuário master paulomarques, com logs, rastreabilidade, controle de acesso e proteção operacional.",
        "🔐"
    )

    st.markdown("### 🧩 Módulos Enterprise")

    modulos = pd.DataFrame(
        [
            {"Módulo": "Dashboard Geral", "Status": "✅ Operacional", "Finalidade": "Indicadores executivos de pricing e competitividade"},
            {"Módulo": "Rede/Loja vs Concorrentes", "Status": "✅ Operacional", "Finalidade": "Comparativo por loja, rede e concorrentes"},
            {"Módulo": "Simulador Inteligente", "Status": "✅ Operacional", "Finalidade": "Simulação de preço, margem e oportunidade"},
            {"Módulo": "Controle de Usuários", "Status": "✅ Operacional", "Finalidade": "Cadastro, bloqueio, reset e expiração"},
            {"Módulo": "Central de Auditoria", "Status": "✅ Operacional", "Finalidade": "Histórico de acessos e navegação"},
            {"Módulo": "Saúde do Sistema", "Status": "✅ Operacional", "Finalidade": "Monitoramento das bases e ambiente"},
            {"Módulo": "Backup Center", "Status": "✅ Operacional", "Finalidade": "Backup, histórico e download"},
            {"Módulo": "Multiempresa", "Status": "🟡 Beta", "Finalidade": "Preparação SaaS para múltiplos clientes"}
        ]
    )

    st.dataframe(modulos, use_container_width=True, hide_index=True)

    st.stop()


# --------------------------------------------------
# ROADMAP DO PRODUTO
# --------------------------------------------------

if pagina == "🧭 Roadmap do Produto":

    if not usuario_pode_ver_multiempresa():
        st.error("Acesso não autorizado.")
        st.stop()

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">Product Strategy</div>
            <h1>🧭 Roadmap do Produto</h1>
            <p>Plano evolutivo da plataforma Eirox Pricing Enterprise.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    legenda_tela("🧭 Roadmap do Produto")

    roadmap = pd.DataFrame(
        [
            {"Versão": "v1.34.0", "Marco": "Produção congelada", "Status": "✅ Concluído", "Objetivo": "Base estável para clientes"},
            {"Versão": "v1.35.0", "Marco": "Controle de Usuários", "Status": "✅ Concluído", "Objetivo": "Governança e segurança"},
            {"Versão": "v1.35.2", "Marco": "Auditoria Avançada", "Status": "✅ Concluído", "Objetivo": "Rastreabilidade de uso"},
            {"Versão": "v1.35.3", "Marco": "Saúde do Sistema", "Status": "✅ Concluído", "Objetivo": "Monitoramento operacional"},
            {"Versão": "v1.35.4", "Marco": "Backup Center", "Status": "✅ Concluído", "Objetivo": "Proteção e recuperação"},
            {"Versão": "v1.35.5", "Marco": "Multiempresa", "Status": "🟡 Beta", "Objetivo": "Preparação SaaS"},
            {"Versão": "v1.36.0", "Marco": "Versão Comercial", "Status": "🔄 Planejado", "Objetivo": "Venda piloto"},
            {"Versão": "v1.37.0", "Marco": "Alertas Inteligentes", "Status": "🔄 Planejado", "Objetivo": "Automação comercial"},
            {"Versão": "v2.0.0", "Marco": "IA Pricing Enterprise", "Status": "🔮 Futuro", "Objetivo": "Recomendação automática avançada"}
        ]
    )

    st.dataframe(roadmap, use_container_width=True, hide_index=True)

    st.markdown("### 🎯 Próximas prioridades")

    p1, p2, p3 = st.columns(3)

    with p1:
        card_enterprise(
            "Alertas Inteligentes",
            "Notificações automáticas para margem baixa, concorrência agressiva, preço fora da estratégia e bases desatualizadas.",
            "🚨"
        )

    with p2:
        card_enterprise(
            "Licenciamento SaaS",
            "Controle de planos, empresas, usuários contratados e módulos liberados por cliente.",
            "💼"
        )

    with p3:
        card_enterprise(
            "IA de Recomendação",
            "Motor inteligente para sugerir preço ideal com base em concorrência, custo, estoque e elasticidade.",
            "🤖"
        )

    st.stop()





# --------------------------------------------------
# MOTOR DE OPORTUNIDADES
# --------------------------------------------------

if pagina == "💰 Motor de Oportunidades":

    if not usuario_pode_ver_motor_oportunidades():
        st.error("Acesso não autorizado.")
        st.stop()

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">Opportunity Engine</div>
            <h1>💰 Motor de Oportunidades</h1>
            <p>Ranking financeiro das maiores oportunidades de ganho por produto, laboratório, categoria e loja.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    legenda_tela("💰 Motor de Oportunidades")

    st.markdown("### ⚙️ Parâmetros do motor")

    p1, p2, p3 = st.columns(3)
    top_n = p1.number_input("Top oportunidades", min_value=10, max_value=1000, value=100, step=10)
    margem_minima = p2.number_input("Margem mínima desejada (%)", min_value=0, max_value=100, value=20, step=1)
    apenas_positivo = p3.selectbox("Exibir apenas ganho positivo", ["Sim", "Não"], index=0)

    col_gerar, col_enviar = st.columns(2)

    if "motor_oportunidades_df" not in st.session_state:
        st.session_state["motor_oportunidades_df"] = pd.DataFrame()

    if col_gerar.button("💰 Gerar Motor de Oportunidades", use_container_width=True):
        with st.spinner("Calculando oportunidades financeiras..."):
            oportunidades_df = gerar_motor_oportunidades(
                top_n=top_n,
                margem_minima=margem_minima,
                apenas_oportunidade_positiva=apenas_positivo == "Sim"
            )
        st.session_state["motor_oportunidades_df"] = oportunidades_df

        if oportunidades_df.empty:
            st.info("Nenhuma oportunidade encontrada com os parâmetros atuais.")
        else:
            salvar_oportunidades(oportunidades_df)
            st.success(f"💰 {len(oportunidades_df)} oportunidades geradas.")

    oportunidades_df = st.session_state.get("motor_oportunidades_df", pd.DataFrame())

    if col_enviar.button("📨 Enviar Top 10 ao Telegram", use_container_width=True):
        if oportunidades_df.empty:
            st.info("Gere as oportunidades antes de enviar.")
        else:
            ok, msg = enviar_oportunidades_telegram(oportunidades_df, limite_envio=10)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    if not oportunidades_df.empty:
        ganho_total = oportunidades_df["Ganho_Potencial"].sum() if "Ganho_Potencial" in oportunidades_df.columns else 0
        ticket_medio = oportunidades_df["Ganho_Potencial"].mean() if "Ganho_Potencial" in oportunidades_df.columns else 0
        produtos = oportunidades_df["Produto"].nunique() if "Produto" in oportunidades_df.columns else len(oportunidades_df)
        labs = oportunidades_df["Laboratório"].nunique() if "Laboratório" in oportunidades_df.columns else 0

        st.markdown("### 🧭 Painel Executivo de Oportunidades")
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Ganho potencial total", f"R$ {_oport_numero_br(ganho_total)}")
        k2.metric("Oportunidades", len(oportunidades_df))
        k3.metric("Ganho médio", f"R$ {_oport_numero_br(ticket_medio)}")
        k4.metric("Produtos únicos", produtos)
        k5.metric("Laboratórios", labs)

        st.markdown("### 🏆 Top oportunidades")
        view = oportunidades_df.copy()

        tipo_filtro = st.multiselect("Filtrar tipo de oportunidade", sorted(view["Tipo_Oportunidade"].dropna().astype(str).unique().tolist()) if "Tipo_Oportunidade" in view.columns else [])
        lab_filtro = st.multiselect("Filtrar laboratório", sorted(view["Laboratório"].dropna().astype(str).unique().tolist()) if "Laboratório" in view.columns else [])

        if tipo_filtro and "Tipo_Oportunidade" in view.columns:
            view = view[view["Tipo_Oportunidade"].astype(str).isin(tipo_filtro)]
        if lab_filtro and "Laboratório" in view.columns:
            view = view[view["Laboratório"].astype(str).isin(lab_filtro)]

        st.dataframe(view, use_container_width=True, hide_index=True)

        st.markdown("### 📊 Ganho por laboratório e categoria")
        g1, g2 = st.columns(2)

        if "Laboratório" in oportunidades_df.columns:
            ganho_lab = oportunidades_df.groupby("Laboratório", dropna=False).agg(Ganho_Potencial=("Ganho_Potencial", "sum")).reset_index().sort_values("Ganho_Potencial", ascending=False).head(15)
            fig_lab = px.bar(ganho_lab, x="Ganho_Potencial", y="Laboratório", orientation="h", title="Top laboratórios por potencial de captura")
            fig_lab.update_layout(height=420, margin=dict(l=10, r=10, t=60, b=10), yaxis=dict(autorange="reversed"))
            g1.plotly_chart(fig_lab, use_container_width=True)

        if "Categoria" in oportunidades_df.columns:
            ganho_cat = oportunidades_df.groupby("Categoria", dropna=False).agg(Ganho_Potencial=("Ganho_Potencial", "sum")).reset_index().sort_values("Ganho_Potencial", ascending=False).head(15)
            fig_cat = px.bar(ganho_cat, x="Ganho_Potencial", y="Categoria", orientation="h", title="Top categorias por potencial de captura")
            fig_cat.update_layout(height=420, margin=dict(l=10, r=10, t=60, b=10), yaxis=dict(autorange="reversed"))
            g2.plotly_chart(fig_cat, use_container_width=True)

        st.markdown("### 📤 Exportação")
        csv_oport = view.to_csv(index=False, sep=";", encoding="utf-8-sig")
        st.download_button("📥 Exportar Oportunidades CSV", data=csv_oport, file_name="motor_oportunidades_eirox.csv", mime="text/csv", use_container_width=True)

    st.markdown("### 📜 Histórico de oportunidades")
    hist_oport = carregar_historico_oportunidades()
    if hist_oport.empty:
        st.info("Nenhum histórico registrado ainda.")
    else:
        st.dataframe(hist_oport.tail(300), use_container_width=True, hide_index=True)

    st.stop()



# --------------------------------------------------
# ALERTAS INTELIGENTES
# --------------------------------------------------

if pagina == "🚨 Alertas Inteligentes":

    if not usuario_pode_ver_alertas_inteligentes():
        st.error("Acesso não autorizado.")
        st.stop()

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">Intelligent Monitoring</div>
            <h1>🚨 Alertas Inteligentes</h1>
            <p>Monitoramento automático de riscos, oportunidades, margem, concorrência, estoque e pesquisa de mercado.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    legenda_tela("🚨 Alertas Inteligentes")

    st.markdown("### ⚙️ Parâmetros dos alertas")

    p1, p2, p3, p4, p5 = st.columns(5)

    limite_margem = p1.number_input("Margem mínima (%)", min_value=0, max_value=100, value=20, step=1)
    limite_diferenca = p2.number_input("Diferença concorrente (%)", min_value=0, max_value=100, value=10, step=1)
    dias_sem_pesquisa = p3.number_input("Dias sem pesquisa", min_value=1, max_value=90, value=7, step=1)
    limite_estoque = p4.number_input("Estoque alto", min_value=0, max_value=10000, value=50, step=10)
    limite_alertas = p5.number_input("Máx. alertas", min_value=10, max_value=1000, value=100, step=10)

    st.markdown("### 🧠 Motor de alertas")

    col_gerar, col_enviar = st.columns(2)

    if "alertas_inteligentes_df" not in st.session_state:
        st.session_state["alertas_inteligentes_df"] = pd.DataFrame()

    if col_gerar.button("🚨 Gerar Alertas Inteligentes", use_container_width=True):
        with st.spinner("Analisando bases e gerando alertas..."):
            alertas_df = gerar_alertas_inteligentes(
                limite_margem=limite_margem,
                limite_diferenca_concorrente=limite_diferenca,
                dias_sem_pesquisa=dias_sem_pesquisa,
                limite_estoque_alto=limite_estoque,
                limite_alertas=limite_alertas
            )

        st.session_state["alertas_inteligentes_df"] = alertas_df

        if alertas_df.empty:
            st.success("🟢 Nenhum alerta crítico encontrado com os parâmetros atuais.")
        else:
            _alerta_salvar(alertas_df.to_dict("records"))
            st.warning(f"🚨 {len(alertas_df)} alertas gerados.")

    alertas_df = st.session_state.get("alertas_inteligentes_df", pd.DataFrame())

    if col_enviar.button("📨 Enviar resumo ao Telegram", use_container_width=True):
        if alertas_df.empty:
            st.info("Gere os alertas antes de enviar.")
        else:
            ok, msg = enviar_alertas_telegram(alertas_df, limite_envio=10)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    if not alertas_df.empty:

        st.markdown("### 📊 Resumo executivo")

        a1, a2, a3, a4 = st.columns(4)

        a1.metric("Alertas", len(alertas_df))
        a2.metric("Alta severidade", int((alertas_df["Severidade"].astype(str) == "Alta").sum()) if "Severidade" in alertas_df.columns else 0)
        a3.metric("Tipos de alerta", alertas_df["Tipo"].nunique() if "Tipo" in alertas_df.columns else 0)
        a4.metric("Produtos únicos", alertas_df["Produto"].nunique() if "Produto" in alertas_df.columns else 0)

        st.markdown("### 🚨 Alertas gerados")

        severidade_filtro = st.multiselect(
            "Filtrar severidade",
            sorted(alertas_df["Severidade"].dropna().astype(str).unique().tolist()) if "Severidade" in alertas_df.columns else []
        )

        tipo_filtro = st.multiselect(
            "Filtrar tipo",
            sorted(alertas_df["Tipo"].dropna().astype(str).unique().tolist()) if "Tipo" in alertas_df.columns else []
        )

        view = alertas_df.copy()

        if severidade_filtro and "Severidade" in view.columns:
            view = view[view["Severidade"].astype(str).isin(severidade_filtro)]

        if tipo_filtro and "Tipo" in view.columns:
            view = view[view["Tipo"].astype(str).isin(tipo_filtro)]

        st.dataframe(view, use_container_width=True, hide_index=True)

        csv_alertas = view.to_csv(index=False, sep=";", encoding="utf-8-sig")

        st.download_button(
            "📥 Exportar Alertas CSV",
            data=csv_alertas,
            file_name="alertas_inteligentes_eirox.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.markdown("### 📜 Histórico de alertas")

    historico_alertas = carregar_historico_alertas()

    if historico_alertas.empty:
        st.info("Nenhum histórico de alerta registrado ainda.")
    else:
        st.dataframe(historico_alertas.tail(300), use_container_width=True, hide_index=True)

    st.stop()



# --------------------------------------------------
# LICENCIAMENTO REAL
# --------------------------------------------------

if pagina == "💼 Licenciamento Real":

    if not usuario_pode_ver_licenciamento_real():
        st.error("Acesso não autorizado.")
        st.stop()

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">SaaS Revenue Control</div>
            <h1>💼 Licenciamento Real</h1>
            <p>Controle real de planos, expiração, limites de usuários, lojas e bloqueio de licença por empresa.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    legenda_tela("💼 Licenciamento Real")

    licencas = carregar_licencas_sistema()
    empresas = carregar_empresas_sistema() if "carregar_empresas_sistema" in globals() else pd.DataFrame()

    empresa_contexto = empresa_contexto_atual() if "empresa_contexto_atual" in globals() else "1"
    metricas = licenca_metricas_empresa(empresa_contexto)
    lic_atual = metricas.get("Licenca", {})
    status_atual = metricas.get("Status", {})

    st.markdown("### 🧭 Painel Executivo da Licença Atual")

    l1, l2, l3, l4, l5 = st.columns(5)

    l1.metric("Plano", lic_atual.get("Plano", "-"))
    l2.metric("Status", status_atual.get("StatusOperacional", "-"))
    l3.metric("Dias restantes", status_atual.get("DiasRestantes", "-"))
    l4.metric("Usuários", f'{metricas.get("UsuariosUsados", 0)} / {metricas.get("MaxUsuarios", 0)}')
    l5.metric("Lojas", f'{metricas.get("LojasUsadas", 0)} / {metricas.get("MaxLojas", 0)}')

    st.markdown("### 📦 Planos disponíveis")

    planos_view = pd.DataFrame(
        [
            {
                "Plano": plano,
                "MaxUsuarios": dados["MaxUsuarios"],
                "MaxLojas": dados["MaxLojas"],
                "Módulos": dados["Modulos"]
            }
            for plano, dados in PLANOS_EIROX.items()
        ]
    )

    st.dataframe(
        planos_view,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### 🏢 Licenças por empresa")

    lic_view = licencas.copy()

    if not lic_view.empty:
        lic_view["DiasRestantes"] = lic_view["DataExpiracao"].apply(dias_restantes_licenca)
        lic_view["StatusOperacional"] = lic_view["EmpresaID"].apply(
            lambda x: status_licenca_empresa(x).get("StatusOperacional", "-")
        )
        lic_view["UsuariosUsados"] = lic_view["EmpresaID"].apply(contar_usuarios_empresa)
        lic_view["LojasUsadas"] = lic_view["EmpresaID"].apply(contar_lojas_empresa)

    st.dataframe(
        lic_view,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### ✍️ Criar ou atualizar licença")

    empresas_labels = []

    if not empresas.empty:
        empresas_labels = [
            f'{row["EmpresaID"]} - {row["Empresa"]}'
            for _, row in empresas.iterrows()
        ]

    if not empresas_labels:
        empresas_labels = ["1 - Marabá - Cliente teste"]

    empresa_label = st.selectbox(
        "Empresa",
        empresas_labels,
        key="lic_empresa_sel"
    )

    empresa_id_sel = empresa_label.split(" - ")[0].strip()
    empresa_nome_sel = empresa_label.split(" - ", 1)[1].strip() if " - " in empresa_label else obter_nome_empresa(empresa_id_sel)

    lic_sel = obter_licenca_empresa(empresa_id_sel) or {}

    with st.form("form_licenciamento_real"):

        plano_form = st.selectbox(
            "Plano",
            list(PLANOS_EIROX.keys()),
            index=list(PLANOS_EIROX.keys()).index(lic_sel.get("Plano", "Starter")) if lic_sel.get("Plano", "Starter") in PLANOS_EIROX else 0
        )

        data_inicio_form = st.text_input(
            "Data início",
            value=lic_sel.get("DataInicio", datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y")),
            placeholder="dd/mm/aaaa"
        )

        data_expiracao_form = st.text_input(
            "Data expiração",
            value=lic_sel.get("DataExpiracao", ""),
            placeholder="dd/mm/aaaa"
        )

        status_form = st.selectbox(
            "Status",
            ["Ativa", "Trial", "Bloqueada", "Cancelada"],
            index=["Ativa", "Trial", "Bloqueada", "Cancelada"].index(lic_sel.get("Status", "Ativa")) if lic_sel.get("Status", "Ativa") in ["Ativa", "Trial", "Bloqueada", "Cancelada"] else 0
        )

        observacao_form = st.text_area(
            "Observação",
            value=lic_sel.get("Observacao", "")
        )

        salvar_licenca = st.form_submit_button(
            "💾 Salvar licença",
            use_container_width=True
        )

    if salvar_licenca:
        ok, msg = criar_ou_atualizar_licenca(
            empresa_id_sel,
            empresa_nome_sel,
            plano_form,
            data_inicio_form,
            data_expiracao_form,
            status_form,
            observacao_form
        )

        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    st.markdown("### 🔒 Regras automáticas")

    regras = pd.DataFrame(
        [
            {"Regra": "Bloqueio por expiração", "Status": "✅ Ativo", "Descrição": "Usuários de empresas expiradas são bloqueados no login."},
            {"Regra": "Limite de usuários", "Status": "✅ Ativo", "Descrição": "Cadastro respeita o limite do plano contratado."},
            {"Regra": "Limite de lojas", "Status": "🟡 Monitorado", "Descrição": "Quantidade de lojas é calculada e exibida para controle comercial."},
            {"Regra": "Master support", "Status": "✅ Ativo", "Descrição": "paulomarques não é bloqueado para suporte e administração."}
        ]
    )

    st.dataframe(
        regras,
        use_container_width=True,
        hide_index=True
    )

    st.stop()



# --------------------------------------------------
# LICENCIAMENTO MULTIEMPRESA
# --------------------------------------------------

if pagina == "💼 Licenciamento Multiempresa":

    if not usuario_pode_ver_multiempresa():
        st.error("Acesso não autorizado.")
        st.stop()

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">Commercial SaaS Model</div>
            <h1>💼 Licenciamento Multiempresa</h1>
            <p>Estrutura comercial sugerida para operação SaaS com múltiplas redes de farmácia.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    legenda_tela("💼 Licenciamento Multiempresa")

    planos = pd.DataFrame(
        [
            {"Plano": "Starter", "Empresas": "1", "Usuários": "Até 5", "Módulos": "Dashboard + Concorrência", "Indicação": "Rede pequena ou piloto"},
            {"Plano": "Professional", "Empresas": "1", "Usuários": "Até 20", "Módulos": "Dashboard + Simulador + Auditoria", "Indicação": "Rede regional"},
            {"Plano": "Enterprise", "Empresas": "Até 5", "Usuários": "Até 100", "Módulos": "Todos os módulos + Backup + Saúde", "Indicação": "Grupo com múltiplas redes"},
            {"Plano": "Enterprise Plus", "Empresas": "Ilimitado", "Usuários": "Sob contrato", "Módulos": "Todos + APIs + IA Pricing", "Indicação": "Operação nacional"}
        ]
    )

    st.markdown("### 📦 Planos sugeridos")
    st.dataframe(planos, use_container_width=True, hide_index=True)

    st.markdown("### 🔐 Regras comerciais recomendadas")

    regras = pd.DataFrame(
        [
            {"Regra": "Isolamento de dados", "Descrição": "Cada empresa visualiza apenas seus próprios dados e usuários."},
            {"Regra": "Usuário master", "Descrição": "Apenas paulomarques ou administradores autorizados podem acessar módulos administrativos."},
            {"Regra": "Backup por cliente", "Descrição": "Backups separados por empresa para segurança e recuperação."},
            {"Regra": "Auditoria por cliente", "Descrição": "Logs vinculados a empresa, usuário, tela e evento."},
            {"Regra": "Módulos por plano", "Descrição": "Funcionalidades liberadas conforme pacote contratado."}
        ]
    )

    st.dataframe(regras, use_container_width=True, hide_index=True)

    card_enterprise(
        "Próximo passo técnico",
        "Criar a tabela PLANOS_EIROX.csv e vincular cada EmpresaID a um plano comercial, quantidade de usuários permitidos e módulos contratados.",
        "🧩"
    )

    st.stop()



# --------------------------------------------------
# MULTIEMPRESA
# --------------------------------------------------

if pagina == "🏢 Multiempresa":

    if not usuario_pode_ver_multiempresa():
        st.error("Acesso não autorizado.")
        st.stop()

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">SaaS Enterprise</div>
            <h1>🏢 Multiempresa</h1>
            <p>Cadastro de empresas, vínculo de usuários, contexto master e preparação para isolamento de dados por cliente.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    empresas = carregar_empresas_sistema()
    usuarios_multi = carregar_usuarios_sistema() if "carregar_usuarios_sistema" in globals() else pd.DataFrame()

    if "EmpresaID" not in usuarios_multi.columns and not usuarios_multi.empty:
        usuarios_multi["EmpresaID"] = "1"

    m1, m2, m3, m4 = st.columns(4)

    total_empresas = len(empresas)
    empresas_ativas = int((empresas["Ativa"].astype(str).str.lower() == "sim").sum()) if not empresas.empty and "Ativa" in empresas.columns else 0
    usuarios_vinculados = int(usuarios_multi["Usuario"].nunique()) if not usuarios_multi.empty and "Usuario" in usuarios_multi.columns else 0
    empresa_contexto_nome = obter_nome_empresa(empresa_contexto_atual())

    m1.metric("Empresas", total_empresas)
    m2.metric("Empresas ativas", empresas_ativas)
    m3.metric("Usuários vinculados", usuarios_vinculados)
    m4.metric("Contexto atual", empresa_contexto_nome)

    aba_empresas, aba_vinculos, aba_isolamento = st.tabs(
        [
            "🏢 Empresas",
            "👥 Usuários por empresa",
            "🔒 Isolamento de dados"
        ]
    )

    with aba_empresas:

        st.markdown("### 🏢 Cadastro de empresas")

        empresas_opcoes = ["Nova empresa"]

        if not empresas.empty:
            empresas_opcoes += [
                f'{row["EmpresaID"]} - {row["Empresa"]}'
                for _, row in empresas.iterrows()
            ]

        empresa_sel = st.selectbox("Selecionar empresa", empresas_opcoes, key="multiempresa_empresa_sel")
        dados_empresa = {}

        if empresa_sel != "Nova empresa":
            empresa_id_sel = empresa_sel.split(" - ")[0].strip()
            linha_emp = empresas[empresas["EmpresaID"].astype(str).str.strip() == empresa_id_sel]
            if not linha_emp.empty:
                dados_empresa = linha_emp.iloc[0].to_dict()

        with st.form("form_multiempresa_empresa"):

            empresa_id_form = st.text_input("EmpresaID", value=dados_empresa.get("EmpresaID", "") if dados_empresa else "")
            empresa_nome_form = st.text_input("Nome da empresa", value=dados_empresa.get("Empresa", "") if dados_empresa else "")
            empresa_ativa_form = st.selectbox("Ativa", ["Sim", "Não"], index=0 if dados_empresa.get("Ativa", "Sim") == "Sim" else 1)

            salvar_empresa = st.form_submit_button("💾 Salvar empresa", use_container_width=True)

        if salvar_empresa:
            ok, msg = criar_ou_atualizar_empresa(empresa_id_form, empresa_nome_form, empresa_ativa_form)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

        st.markdown("### 📋 Empresas cadastradas")
        st.dataframe(empresas, use_container_width=True, hide_index=True)

    with aba_vinculos:

        st.markdown("### 👥 Usuários vinculados por empresa")

        if usuarios_multi.empty:
            st.info("Nenhum usuário encontrado.")
        else:
            usuarios_view = usuarios_multi.copy()
            usuarios_view["Empresa"] = usuarios_view["EmpresaID"].apply(obter_nome_empresa)

            colunas_usuarios = ["Usuario", "Nome", "Perfil", "EmpresaID", "Empresa", "Ativo", "Expira_Em", "Forcar_Reset"]
            colunas_usuarios = [c for c in colunas_usuarios if c in usuarios_view.columns]

            st.dataframe(usuarios_view[colunas_usuarios], use_container_width=True, hide_index=True)

        st.markdown("### 🔁 Alterar empresa de um usuário")

        if not usuarios_multi.empty and not empresas.empty:

            usuario_vinculo = st.selectbox("Usuário", sorted(usuarios_multi["Usuario"].dropna().astype(str).unique().tolist()), key="multi_usuario_vinculo")

            empresas_labels = [
                f'{row["EmpresaID"]} - {row["Empresa"]}'
                for _, row in empresas.iterrows()
                if str(row.get("Ativa", "Sim")).lower() == "sim"
            ]

            empresa_vinculo_label = st.selectbox("Empresa", empresas_labels, key="multi_empresa_vinculo")

            if st.button("🔗 Vincular usuário à empresa", use_container_width=True):

                empresa_vinculo_id = empresa_vinculo_label.split(" - ")[0].strip()
                base_u = carregar_usuarios_sistema()

                if "EmpresaID" not in base_u.columns:
                    base_u["EmpresaID"] = "1"

                idxs = base_u.index[base_u["Usuario"].astype(str).str.lower() == str(usuario_vinculo).lower()]

                if len(idxs) == 0:
                    st.error("Usuário não encontrado.")
                else:
                    idx = idxs[0]
                    base_u.loc[idx, "EmpresaID"] = empresa_vinculo_id
                    salvar_usuarios_sistema(base_u)

                    try:
                        registrar_log_usuario("Vínculo Multiempresa", usuario_vinculo, f"EmpresaID={empresa_vinculo_id} | Empresa={obter_nome_empresa(empresa_vinculo_id)}")
                    except Exception:
                        pass

                    st.success("Usuário vinculado com sucesso.")
                    st.rerun()

    with aba_isolamento:

        st.markdown("### 🔒 Status de isolamento por EmpresaID")

        st.info(
            "O isolamento multiempresa já está preparado. Quando as bases possuírem a coluna EmpresaID, "
            "os dados poderão ser filtrados pelo contexto da empresa do usuário. "
            "Bases sem EmpresaID continuam funcionando no modelo atual para manter compatibilidade."
        )

        bases_check = []

        for nome_base, nome_var in [
            ("Analise_Pricing", "df"),
            ("VENDA_TESTE", "historico"),
            ("VENDA_FINAL_TESTE", "venda_rede"),
            ("COMPRA_TESTE", "compra"),
            ("ESTOQUE_TESTE", "estoque")
        ]:
            try:
                base_ref = globals().get(nome_var, pd.DataFrame())
                bases_check.append(
                    {
                        "Base": nome_base,
                        "Possui EmpresaID": "Sim" if isinstance(base_ref, pd.DataFrame) and "EmpresaID" in base_ref.columns else "Não",
                        "Registros": len(base_ref) if isinstance(base_ref, pd.DataFrame) else 0,
                        "Status": "🟢 Isolável" if isinstance(base_ref, pd.DataFrame) and "EmpresaID" in base_ref.columns else "🟡 Compatibilidade"
                    }
                )
            except Exception:
                pass

        st.dataframe(pd.DataFrame(bases_check), use_container_width=True, hide_index=True)

    st.stop()



# --------------------------------------------------
# BACKUP CENTER
# --------------------------------------------------

if pagina == "📦 Backup Center":

    if not usuario_pode_ver_auditoria():
        st.error("Acesso não autorizado.")
        st.stop()

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">Proteção e Recuperação</div>
            <h1>📦 Backup Center</h1>
            <p>Geração, controle, histórico e download de backups oficiais do Eirox Pricing Enterprise.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    ultimo_backup = _backup_ultimo()
    backups_df = listar_backups_eirox()
    espaco_total = _backup_espaco_total()

    qtd_backups = len(backups_df)
    ultimo_data = ultimo_backup.get("Criado em", "-") if ultimo_backup else "-"
    status_backup = "🟢 Protegido" if qtd_backups > 0 else "🟡 Sem backup"

    st.markdown("### 🧭 Painel Executivo de Backup")

    b1, b2, b3, b4, b5 = st.columns(5)

    b1.metric("Status", status_backup)
    b2.metric("Backups disponíveis", qtd_backups)
    b3.metric("Espaço utilizado", _backup_tamanho_formatado(espaco_total))
    b4.metric("Último backup", ultimo_data)
    b5.metric("Versão", VERSAO_APP)

    st.markdown("### 📋 Itens protegidos")

    status_alvos = _backup_status_alvos()

    st.dataframe(
        status_alvos,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### 📦 Gerar backup")

    nome_manual = st.text_input(
        "Nome do backup",
        value=f"BACKUP_EIROX_PRICING_{VERSAO_APP}_{_backup_agora_tag()}",
        help="Você pode manter o nome automático ou alterar."
    )

    col_gerar, col_limpar = st.columns(2)

    if col_gerar.button(
        "📦 Gerar Backup Completo",
        use_container_width=True
    ):

        with st.spinner("Gerando backup completo do Eirox..."):
            resultado = gerar_backup_eirox(nome_manual)

        if resultado.get("ok"):
            st.success(
                f"Backup gerado com sucesso: {resultado.get('nome')} "
                f"({_backup_tamanho_formatado(resultado.get('tamanho', 0))})"
            )
            st.rerun()
        else:
            st.error(
                f"Falha ao gerar backup: {resultado.get('erro')}"
            )

    if col_limpar.button(
        "🧹 Manter apenas últimos 10 backups",
        use_container_width=True
    ):

        removidos = limpar_backups_antigos(10)

        st.success(
            f"Limpeza concluída. Backups removidos: {removidos}"
        )

        st.rerun()

    st.markdown("### 🗂️ Histórico de backups")

    backups_df = listar_backups_eirox()

    if backups_df.empty:
        st.info("Nenhum backup gerado ainda.")
    else:
        st.dataframe(
            backups_df[
                [
                    "Arquivo",
                    "Tamanho",
                    "Criado em"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

        st.markdown("### ⬇️ Download de backup")

        backup_opcoes = backups_df["Arquivo"].tolist()

        backup_sel = st.selectbox(
            "Selecione o backup",
            backup_opcoes
        )

        linha_backup = backups_df[
            backups_df["Arquivo"] == backup_sel
        ]

        if not linha_backup.empty:
            caminho_backup = Path(
                linha_backup.iloc[0]["Caminho"]
            )

            if caminho_backup.exists():
                with open(caminho_backup, "rb") as f:
                    dados_backup = f.read()

                st.download_button(
                    "⬇️ Baixar backup selecionado",
                    data=dados_backup,
                    file_name=caminho_backup.name,
                    mime="application/zip",
                    use_container_width=True
                )

    st.markdown("### ⚠️ Observações de segurança")

    st.info(
        "Os Secrets do Streamlit Cloud não são exportados automaticamente por segurança. "
        "Mantenha uma cópia segura separada das chaves TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID."
    )

    st.stop()



# --------------------------------------------------
# SAÚDE DO SISTEMA
# --------------------------------------------------

if pagina == "🟢 Saúde do Sistema":

    if not usuario_pode_ver_auditoria():
        st.error("Acesso não autorizado.")
        st.stop()

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">Eirox Health Center</div>
            <h1>🟢 Saúde do Sistema</h1>
            <p>Monitoramento das bases, performance, integridade, usuários, auditoria e integrações.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    inicio_health = time.time()
    saude_bases = gerar_saude_bases()

    bases_monitoradas = len(saude_bases)
    arquivos_total = int(saude_bases["Arquivos"].sum()) if "Arquivos" in saude_bases.columns else 0
    registros_total = int(saude_bases["Registros"].sum()) if "Registros" in saude_bases.columns else 0

    ultima_atualizacao = "-"
    try:
        temp_datas = pd.to_datetime(saude_bases["Última Atualização"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
        if temp_datas.notna().any():
            ultima_atualizacao = temp_datas.max().strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        pass

    tempo_total = round(time.time() - inicio_health, 2)

    qtd_ok = int(saude_bases["Status"].astype(str).str.contains("OK", na=False).sum()) if "Status" in saude_bases.columns else 0
    qtd_alerta = int(saude_bases["Status"].astype(str).str.contains("Desatualizada", na=False).sum()) if "Status" in saude_bases.columns else 0
    qtd_erro = int(saude_bases["Status"].astype(str).str.contains("Não encontrada", na=False).sum()) if "Status" in saude_bases.columns else 0

    saude_geral = "🟢 Sistema saudável"
    if qtd_erro > 0:
        saude_geral = "🔴 Atenção crítica"
    elif qtd_alerta > 0:
        saude_geral = "🟡 Atenção"

    st.markdown("### 🧭 Painel Executivo de Saúde")

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Bases monitoradas", bases_monitoradas)
    k2.metric("Arquivos encontrados", _health_numero_br(arquivos_total))
    k3.metric("Registros totais", _health_numero_br(registros_total))
    k4.metric("Última atualização", ultima_atualizacao)
    k5.metric("Tempo de leitura", f"{tempo_total}s")

    st.markdown(
        f"""
        <div class="eirox-card">
            <div class="eirox-section-title">Status Geral</div>
            <h2 style="margin:0;">{saude_geral}</h2>
            <p>Bases OK: {qtd_ok} | Alertas: {qtd_alerta} | Erros: {qtd_erro}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("### 📁 Status das bases")

    saude_view = saude_bases.copy()
    if "Registros" in saude_view.columns:
        saude_view["Registros"] = saude_view["Registros"].apply(_health_numero_br)

    st.dataframe(
        saude_view[[c for c in ["Base", "Status", "Arquivos", "Registros", "Última Atualização", "Tempo Leitura (s)", "Erros"] if c in saude_view.columns]],
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### 🔐 Segurança e operação")

    total_usuarios, usuarios_ativos, usuarios_bloqueados = health_status_usuarios()
    logs = carregar_logs_acesso() if "carregar_logs_acesso" in globals() else pd.DataFrame()
    usuarios_ativos_hoje = 0

    try:
        if not logs.empty and "Data_Hora" in logs.columns and "Usuario" in logs.columns:
            logs_temp = logs.copy()
            logs_temp["Data_Hora_dt"] = pd.to_datetime(logs_temp["Data_Hora"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
            hoje_txt = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y")
            logs_temp["Data"] = logs_temp["Data_Hora_dt"].dt.strftime("%d/%m/%Y")
            usuarios_ativos_hoje = logs_temp.loc[logs_temp["Data"] == hoje_txt, "Usuario"].nunique()
    except Exception:
        pass

    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("Telegram", health_status_telegram())
    s2.metric("Usuários cadastrados", total_usuarios)
    s3.metric("Usuários ativos", usuarios_ativos)
    s4.metric("Usuários bloqueados", usuarios_bloqueados)
    s5.metric("Último login", health_ultimo_login())

    st.metric("Usuários ativos hoje", usuarios_ativos_hoje)

    st.markdown("### 🔍 Diagnóstico automático")

    if st.button("🔍 Executar Diagnóstico", use_container_width=True):
        diag = diagnostico_integridade_basico()

        if diag.empty:
            st.info("Nenhum diagnóstico disponível.")
        else:
            total_ocorrencias = int(diag.loc[~diag["Status"].astype(str).str.contains("OK", na=False), "Ocorrências"].sum())

            if total_ocorrencias == 0:
                st.success("🟢 Sistema saudável. Nenhuma inconsistência crítica encontrada.")
            else:
                st.warning(f"🟡 Foram encontradas {total_ocorrencias:,} ocorrências para análise.".replace(",", "."))

            st.dataframe(diag, use_container_width=True, hide_index=True)

            csv_diag = diag.to_csv(index=False, sep=";", encoding="utf-8-sig")
            st.download_button("📥 Exportar Diagnóstico CSV", data=csv_diag, file_name="diagnostico_saude_sistema.csv", mime="text/csv", use_container_width=True)

    st.markdown("### 📊 Histórico de atualização das bases")
    st.dataframe(saude_bases, use_container_width=True, hide_index=True)

    csv_health = saude_bases.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button("📥 Exportar Saúde do Sistema CSV", data=csv_health, file_name="saude_sistema_eirox.csv", mime="text/csv", use_container_width=True)

    st.stop()



# --------------------------------------------------
# CENTRAL DE AUDITORIA AVANÇADA
# --------------------------------------------------

if pagina == "🔐 Central de Auditoria":

    if not usuario_pode_ver_auditoria():
        st.error("Acesso não autorizado.")
        st.stop()

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">Auditoria Enterprise</div>
            <h1>🔐 Central de Auditoria Avançada</h1>
            <p>Histórico de acessos, tempo de uso, telas mais acessadas, usuários ativos e exportação executiva.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    logs = carregar_logs_acesso()

    if logs.empty:
        st.info("Ainda não existem logs registrados.")
        st.stop()

    logs_view = logs.copy()

    if "Data_Hora_dt" not in logs_view.columns and "Data_Hora" in logs_view.columns:
        logs_view["Data_Hora_dt"] = pd.to_datetime(
            logs_view["Data_Hora"],
            format="%d/%m/%Y %H:%M:%S",
            errors="coerce"
        )

    if "Data_Hora_dt" in logs_view.columns:
        logs_view["Data"] = logs_view["Data_Hora_dt"].dt.strftime("%d/%m/%Y")
        logs_view["Hora"] = logs_view["Data_Hora_dt"].dt.strftime("%H:%M:%S")
    else:
        logs_view["Data"] = ""
        logs_view["Hora"] = ""

    st.markdown("### 🔎 Filtros")

    f1, f2, f3, f4 = st.columns(4)

    usuarios = sorted(logs_view["Usuario"].dropna().astype(str).unique()) if "Usuario" in logs_view.columns else []
    eventos = sorted(logs_view["Evento"].dropna().astype(str).unique()) if "Evento" in logs_view.columns else []
    telas = sorted(logs_view["Tela"].dropna().astype(str).unique()) if "Tela" in logs_view.columns else []
    datas = sorted(logs_view["Data"].dropna().astype(str).unique()) if "Data" in logs_view.columns else []

    filtro_usuario = f1.multiselect("Usuário", usuarios)
    filtro_evento = f2.multiselect("Evento", eventos)
    filtro_tela = f3.multiselect("Tela", telas)
    filtro_data = f4.multiselect("Data", datas)

    if filtro_usuario and "Usuario" in logs_view.columns:
        logs_view = logs_view[logs_view["Usuario"].astype(str).isin(filtro_usuario)]

    if filtro_evento and "Evento" in logs_view.columns:
        logs_view = logs_view[logs_view["Evento"].astype(str).isin(filtro_evento)]

    if filtro_tela and "Tela" in logs_view.columns:
        logs_view = logs_view[logs_view["Tela"].astype(str).isin(filtro_tela)]

    if filtro_data and "Data" in logs_view.columns:
        logs_view = logs_view[logs_view["Data"].astype(str).isin(filtro_data)]

    # KPIs avançados
    hoje_txt = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y")

    eventos_total = len(logs_view)

    usuarios_unicos = (
        logs_view["Usuario"].nunique()
        if "Usuario" in logs_view.columns
        else 0
    )

    usuarios_ativos_hoje = (
        logs_view.loc[
            logs_view["Data"].astype(str) == hoje_txt,
            "Usuario"
        ].nunique()
        if "Data" in logs_view.columns and "Usuario" in logs_view.columns
        else 0
    )

    ultima_acao = "-"

    if "Data_Hora_dt" in logs_view.columns and logs_view["Data_Hora_dt"].notna().any():
        ultima_acao = (
            logs_view
            .sort_values("Data_Hora_dt", ascending=False)
            ["Data_Hora"]
            .iloc[0]
        )

    tela_mais_acessada = "-"

    if "Tela" in logs_view.columns and not logs_view.empty:
        telas_validas = logs_view[
            logs_view["Tela"].astype(str).str.strip().ne("")
        ]

        if not telas_validas.empty:
            tela_mais_acessada = telas_validas["Tela"].value_counts().idxmax()

    tempo_medio_uso = "Não disponível"

    try:
        if "Evento" in logs_view.columns and "Data_Hora_dt" in logs_view.columns and "Usuario" in logs_view.columns:
            base_tempo = logs_view.dropna(subset=["Data_Hora_dt"]).copy()

            sessoes = []

            for usuario, grupo in base_tempo.groupby("Usuario"):
                grupo = grupo.sort_values("Data_Hora_dt")

                logins = grupo[grupo["Evento"].astype(str).eq("Login")]

                for _, login_row in logins.iterrows():
                    inicio = login_row["Data_Hora_dt"]
                    posteriores = grupo[grupo["Data_Hora_dt"] >= inicio]
                    fim = posteriores["Data_Hora_dt"].max()

                    if pd.notna(inicio) and pd.notna(fim):
                        minutos = max(0, (fim - inicio).total_seconds() / 60)
                        if minutos <= 480:
                            sessoes.append(minutos)

            if sessoes:
                media = sum(sessoes) / len(sessoes)
                horas = int(media // 60)
                minutos = int(media % 60)

                if horas > 0:
                    tempo_medio_uso = f"{horas}h {minutos}min"
                else:
                    tempo_medio_uso = f"{minutos}min"

    except Exception:
        tempo_medio_uso = "Não disponível"

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Usuários ativos hoje", usuarios_ativos_hoje)
    c2.metric("Tempo médio de uso", tempo_medio_uso)
    c3.metric("Tela mais acessada", tela_mais_acessada)
    c4.metric("Último acesso", ultima_acao)
    c5.metric("Eventos filtrados", f"{eventos_total:,}".replace(",", "."))

    st.markdown("### 📈 Gráficos de uso")

    # Acessos por dia
    if "Data" in logs_view.columns and not logs_view.empty:
        acessos_dia = (
            logs_view
            .groupby("Data", dropna=False)
            .size()
            .reset_index(name="Acessos")
        )

        try:
            acessos_dia["_dt"] = pd.to_datetime(
                acessos_dia["Data"],
                format="%d/%m/%Y",
                errors="coerce"
            )

            acessos_dia = (
                acessos_dia
                .sort_values("_dt")
                .drop(columns=["_dt"])
            )
        except Exception:
            pass

        fig_dia = px.line(
            acessos_dia,
            x="Data",
            y="Acessos",
            markers=True,
            title="Acessos por dia"
        )

        fig_dia.update_layout(
            height=360,
            margin=dict(l=10, r=10, t=60, b=10)
        )

        st.plotly_chart(
            fig_dia,
            use_container_width=True
        )

    else:
        acessos_dia = pd.DataFrame(columns=["Data", "Acessos"])

    g1, g2 = st.columns(2)

    # Acessos por usuário
    if "Usuario" in logs_view.columns and not logs_view.empty:
        acessos_usuario = (
            logs_view
            .groupby("Usuario", dropna=False)
            .size()
            .reset_index(name="Acessos")
            .sort_values("Acessos", ascending=False)
            .head(15)
        )

        fig_usuario = px.bar(
            acessos_usuario,
            x="Acessos",
            y="Usuario",
            orientation="h",
            title="Acessos por usuário"
        )

        fig_usuario.update_layout(
            height=420,
            margin=dict(l=10, r=10, t=60, b=10),
            yaxis=dict(autorange="reversed")
        )

        g1.plotly_chart(
            fig_usuario,
            use_container_width=True
        )

    else:
        acessos_usuario = pd.DataFrame(columns=["Usuario", "Acessos"])

    # Acessos por tela
    if "Tela" in logs_view.columns and not logs_view.empty:
        acessos_tela = (
            logs_view[
                logs_view["Tela"]
                .astype(str)
                .str.strip()
                .ne("")
            ]
            .groupby("Tela", dropna=False)
            .size()
            .reset_index(name="Acessos")
            .sort_values("Acessos", ascending=False)
            .head(15)
        )

        fig_tela = px.bar(
            acessos_tela,
            x="Acessos",
            y="Tela",
            orientation="h",
            title="Acessos por tela"
        )

        fig_tela.update_layout(
            height=420,
            margin=dict(l=10, r=10, t=60, b=10),
            yaxis=dict(autorange="reversed")
        )

        g2.plotly_chart(
            fig_tela,
            use_container_width=True
        )

    else:
        acessos_tela = pd.DataFrame(columns=["Tela", "Acessos"])

    st.markdown("### 📊 Rankings executivos")

    r1, r2 = st.columns(2)

    if all(c in logs_view.columns for c in ["Usuario", "Nome", "Perfil"]):
        ranking_usuarios = (
            logs_view
            .groupby(["Usuario", "Nome", "Perfil"], dropna=False)
            .agg(
                Eventos=("Evento", "count"),
                Ultimo_Acesso=("Data_Hora", "max")
            )
            .reset_index()
            .sort_values("Eventos", ascending=False)
        )

        r1.dataframe(
            ranking_usuarios,
            use_container_width=True,
            hide_index=True
        )
    else:
        ranking_usuarios = pd.DataFrame()

    if "Tela" in logs_view.columns:
        ranking_telas = (
            logs_view[
                logs_view["Tela"]
                .astype(str)
                .str.strip()
                .ne("")
            ]
            .groupby("Tela", dropna=False)
            .agg(Acessos=("Evento", "count"))
            .reset_index()
            .sort_values("Acessos", ascending=False)
        )

        r2.dataframe(
            ranking_telas,
            use_container_width=True,
            hide_index=True
        )
    else:
        ranking_telas = pd.DataFrame()

    st.markdown("### 📋 Histórico detalhado")

    logs_detalhe = logs_view.copy()

    if "Data_Hora_dt" in logs_detalhe.columns:
        logs_detalhe = logs_detalhe.sort_values(
            "Data_Hora_dt",
            ascending=False
        )

    colunas_exibir = [
        "Data_Hora",
        "Usuario",
        "Nome",
        "Perfil",
        "Evento",
        "Tela",
        "Detalhe",
        "Latitude",
        "Longitude",
        "Precisao_Metros",
        "Status_Localizacao",
        "Ambiente",
        "Versao"
    ]

    colunas_exibir = [
        c for c in colunas_exibir
        if c in logs_detalhe.columns
    ]

    st.dataframe(
        logs_detalhe[colunas_exibir],
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### 📤 Exportação")

    csv_export = logs_detalhe[colunas_exibir].to_csv(
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    col_exp1, col_exp2 = st.columns(2)

    col_exp1.download_button(
        "📥 Exportar Auditoria CSV",
        data=csv_export,
        file_name="auditoria_eirox_pricing.csv",
        mime="text/csv",
        use_container_width=True
    )

    xlsx_export = exportar_auditoria_excel(
        logs_detalhe[colunas_exibir],
        ranking_usuarios,
        ranking_telas,
        acessos_dia
    )

    col_exp2.download_button(
        "📊 Exportar Auditoria.xlsx",
        data=xlsx_export,
        file_name="auditoria_eirox_pricing.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        disabled=not bool(xlsx_export)
    )

    st.stop()

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">Auditoria Enterprise</div>
            <h1>🔐 Central de Auditoria</h1>
            <p>Histórico de acessos, navegação, usuários, telas acessadas e eventos do sistema.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    logs = carregar_logs_acesso()

    if logs.empty:
        st.info("Ainda não existem logs registrados.")
        st.stop()

    logs_view = logs.copy()

    c1, c2, c3, c4, c5 = st.columns(5)

    eventos_total = len(logs_view)
    usuarios_unicos = logs_view["Usuario"].nunique() if "Usuario" in logs_view.columns else 0
    logins = int((logs_view["Evento"].astype(str) == "Login").sum()) if "Evento" in logs_view.columns else 0
    navegacoes = int((logs_view["Evento"].astype(str) == "Navegação").sum()) if "Evento" in logs_view.columns else 0
    ultima_acao = "-"

    if "Data_Hora_dt" in logs_view.columns and logs_view["Data_Hora_dt"].notna().any():
        ultima_acao = logs_view.sort_values("Data_Hora_dt", ascending=False)["Data_Hora"].iloc[0]

    c1.metric("Eventos", f"{eventos_total:,}".replace(",", "."))
    c2.metric("Usuários únicos", usuarios_unicos)
    c3.metric("Logins", logins)
    c4.metric("Navegações", navegacoes)
    c5.metric("Última ação", ultima_acao)

    st.markdown("### 🔎 Filtros")

    f1, f2, f3 = st.columns(3)

    usuarios = sorted(logs_view["Usuario"].dropna().astype(str).unique()) if "Usuario" in logs_view.columns else []
    eventos = sorted(logs_view["Evento"].dropna().astype(str).unique()) if "Evento" in logs_view.columns else []
    telas = sorted(logs_view["Tela"].dropna().astype(str).unique()) if "Tela" in logs_view.columns else []

    filtro_usuario = f1.multiselect("Usuário", usuarios)
    filtro_evento = f2.multiselect("Evento", eventos)
    filtro_tela = f3.multiselect("Tela", telas)

    if filtro_usuario:
        logs_view = logs_view[logs_view["Usuario"].astype(str).isin(filtro_usuario)]
    if filtro_evento:
        logs_view = logs_view[logs_view["Evento"].astype(str).isin(filtro_evento)]
    if filtro_tela:
        logs_view = logs_view[logs_view["Tela"].astype(str).isin(filtro_tela)]

    st.markdown("### 📊 Ranking de usuários")

    if all(c in logs_view.columns for c in ["Usuario", "Nome", "Perfil"]):
        ranking_usuarios = (
            logs_view
            .groupby(["Usuario", "Nome", "Perfil"], dropna=False)
            .size()
            .reset_index(name="Eventos")
            .sort_values("Eventos", ascending=False)
        )
        st.dataframe(ranking_usuarios, use_container_width=True, hide_index=True)

    st.markdown("### 🧭 Ranking de telas acessadas")

    if "Tela" in logs_view.columns:
        ranking_telas = (
            logs_view
            .groupby("Tela", dropna=False)
            .size()
            .reset_index(name="Acessos")
            .sort_values("Acessos", ascending=False)
        )
        st.dataframe(ranking_telas, use_container_width=True, hide_index=True)

    st.markdown("### 📋 Histórico detalhado")

    if "Data_Hora_dt" in logs_view.columns:
        logs_view = logs_view.sort_values("Data_Hora_dt", ascending=False)

    colunas = [
        "Data_Hora", "Usuario", "Nome", "Perfil", "Evento", "Tela", "Detalhe",
        "Latitude", "Longitude", "Precisao_Metros", "Status_Localizacao",
        "Ambiente", "Versao"
    ]
    colunas = [c for c in colunas if c in logs_view.columns]

    st.dataframe(logs_view[colunas], use_container_width=True, hide_index=True)

    csv_export = logs_view[colunas].to_csv(index=False, sep=";", encoding="utf-8-sig")

    st.download_button(
        "📥 Exportar Auditoria CSV",
        data=csv_export,
        file_name="auditoria_eirox_pricing.csv",
        mime="text/csv",
        use_container_width=True
    )

    st.stop()



# --------------------------------------------------
# SUGESTÃO INTELIGENTE DE PESQUISA DE PREÇO
# --------------------------------------------------

if pagina == "🎯 Sugestão de Pesquisa":

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">Inteligência de Campo</div>
            <h1>🎯 Sugestão Inteligente de Pesquisa de Preço</h1>
            <p>Planejamento operacional com 380 marcas por dia, baseado no faturamento da VENDA_FINAL_TESTE.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    if not isinstance(venda_rede, pd.DataFrame) or venda_rede.empty:
        st.warning("A base VENDA_FINAL_TESTE não está carregada.")
        st.stop()

    base_pesquisa = venda_rede.copy()
    base_pesquisa.columns = base_pesquisa.columns.astype(str).str.strip()

    def _sp_coluna(base, exatos, contem=None):
        contem = contem or []

        for alvo in exatos:
            for col in base.columns:
                if str(col).strip().lower() == str(alvo).strip().lower():
                    return col

        for termo in contem:
            termo = str(termo).lower()
            for col in base.columns:
                if termo in str(col).lower():
                    return col

        return None

    def _sp_numero(serie):
        if isinstance(serie, pd.Series):
            s = (
                serie.astype(str)
                .str.strip()
                .str.replace("R$", "", regex=False)
                .str.replace("%", "", regex=False)
                .str.replace(" ", "", regex=False)
            )

            tem_virgula = s.str.contains(",", regex=False)

            s_br = (
                s[tem_virgula]
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
            )

            s_us = (
                s[~tem_virgula]
                .str.replace(",", "", regex=False)
            )

            out = pd.Series(index=serie.index, dtype="float64")
            out.loc[s_br.index] = pd.to_numeric(s_br, errors="coerce")
            out.loc[s_us.index] = pd.to_numeric(s_us, errors="coerce")
            return out

        return pd.to_numeric(serie, errors="coerce")

    def _sp_marca(texto):
        """
        Extrai a marca produto pela descrição.
        Não usa API externa e não altera outras telas.
        """

        texto = str(texto).strip().upper()

        if not texto or texto in ["NAN", "NONE"]:
            return "SEM MARCA"

        # Remove fabricante/laboratório entre parênteses. Ex.: (EMS)
        texto = re.sub(r"\([^)]*\)", " ", texto)

        texto = (
            texto.replace("(A) -", " ")
            .replace("(B) -", " ")
            .replace("(C) -", " ")
            .replace("-", " ")
            .replace("/", " ")
            .replace(".", " ")
            .replace(",", " ")
        )

        texto = re.sub(r"\s+", " ", texto).strip()

        tokens = [
            re.sub(r"[^A-Z0-9ÁÉÍÓÚÂÊÔÃÕÇ]", "", t)
            for t in texto.split()
            if str(t).strip()
        ]

        tokens = [t for t in tokens if t]

        if not tokens:
            return "SEM MARCA"

        invalidos = {
            "KIT", "CR", "CREME", "SAB", "SABONETE", "LIQ", "LIQUIDO", "LÍQUIDO",
            "LEITE", "FRALDA", "FRALDAS", "ROUPA", "INTIMA", "ÍNTIMA",
            "DESODORANTE", "DESOD", "AER", "AEROSSOL", "SPRAY",
            "CAP", "CAPS", "CAPSULA", "CAPSULAS", "CÁPSULA", "CÁPSULAS",
            "CP", "COMP", "COMPRIMIDO", "COMPRIMIDOS", "GTS", "GOTAS",
            "ML", "MG", "MCG", "GR", "G", "POM", "POMADA", "SOL", "SOLUCAO",
            "SOLUÇÃO", "XPE", "SUSP", "CX", "UN", "UND", "UNIDADE", "UNIDADES",
            "COM", "SEM", "REFIL", "PRO", "PLUS", "MEGA", "GIGA", "JUNIOR",
            "ADULTO", "INFANTIL", "BABY", "PANTS", "SHORTINHO", "DESC", "PROMO",
            "ORIGINAL", "TRAD", "FPS", "COL", "GEL", "AZ", "OMEGA", "BAG",
            "CONFORT", "CONFORTO", "MAX", "TOTAL", "CARE",
            "EMS", "EUROFARMA", "CIMED", "MEDLEY", "ACHE", "ACHÉ", "BIOLAB",
            "PRATI", "DONADUZZI", "NATULAB", "TEUTO", "GEOLAB", "HYPERA",
            "OPPELLA", "SANOFI", "BAYER", "GSK", "PFIZER", "SANDOZ", "MERCK",
            "NOVARTIS", "ASTRAZENECA", "LIBBS", "GERMED", "LEGRAND"
        }

        marcas_conhecidas = [
            "DORFLEX", "NEOSALDINA", "NOVALGINA", "BUSCOPAN", "TANDRILAX",
            "TYLENOL", "ADVIL", "ALIVIUM", "VICK", "BENEGRIP", "CORISTINA",
            "SORINE", "NEOSORO", "RINOSORO", "SALONPAS", "BEPANTOL",
            "CICATRICURE", "DERMAONE", "NIVEA", "DOVE", "REXONA", "MONANGE",
            "GRANADO", "PHEBO", "JOHNSON", "NEUTROGENA", "PAMPERS",
            "MAMYPOKO", "BABYSEC", "HUGGIES", "PLENITUD", "TENA", "HIPOPO",
            "NINHO", "NAN", "APTAMIL", "MILNUTRI", "NESTOGENO", "SUSTAGEN",
            "ENSURE", "NUTREN", "PEDIASURE", "FORXIGA", "XIGDUO", "JARDIANCE",
            "OZEMPIC", "MOUNJARO", "RYBELSUS", "GLIFAGE", "JANUVIA", "GALVUS",
            "BRASART", "SELOZOK", "CONCOR", "ARADOIS", "DIOVAN", "NEXIUM",
            "LOSEC", "PURAN", "EUTHYROX", "LEVOID", "EXPEC", "ABRILAR",
            "MUCOSOLVAN", "PROTOVIT", "REDOXON", "CENTRUM", "LAVITAN", "DORIL",
            "SONRISAL", "ENGOV", "ENO", "EPAREMA", "LUFTAL", "CIMEGRIPE",
            "MULTIGRIP", "RESFENOL", "APRACUR", "INTIMUS", "CAREFREE", "CARMED",
            "SUNDOWN", "CERAVE", "VICHY", "ISDIN", "EPISOL", "MUSTELA",
            "MINANCORA", "HIPOGLOS", "DAPAGLIFLOZINA"
        ]

        texto_busca = " ".join(tokens)

        for marca in sorted(marcas_conhecidas, key=len, reverse=True):
            if re.search(r"(^|\s)" + re.escape(marca) + r"($|\s)", texto_busca):
                return marca

        # Fraldas: marca geralmente vem logo depois de FRALDA/FRALDAS.
        for termo in ["FRALDA", "FRALDAS"]:
            if termo in tokens:
                idx = tokens.index(termo)

                if idx + 1 < len(tokens):
                    candidato = tokens[idx + 1]

                    if candidato not in invalidos and not candidato.isdigit() and len(candidato) > 2:
                        return candidato

        # Leites: marca geralmente vem depois de LEITE.
        if "LEITE" in tokens:
            idx = tokens.index("LEITE")

            if idx + 1 < len(tokens):
                candidato = tokens[idx + 1]

                if candidato not in invalidos and not candidato.isdigit() and len(candidato) > 2:
                    return candidato

        # Regra geral: primeira palavra útil da descrição.
        for token in tokens:
            if token in invalidos:
                continue

            if token.isdigit():
                continue

            if re.match(r"^\d+(MG|ML|MCG|G|UN|UND)$", token):
                continue

            if len(token) <= 2:
                continue

            return token

        return "SEM MARCA"


    col_ean = _sp_coluna(
        base_pesquisa,
        ["EAN", "EAN (GTIN)", "GTIN", "Cód. Barras/Etiq.", "Cod. Barras/Etiq.", "Código de Barras", "Codigo de Barras"],
        ["ean", "gtin", "barras", "etiq"]
    )

    col_venda = _sp_coluna(
        base_pesquisa,
        ["Venda", "Valor Venda", "Faturamento", "Valor Total", "Total Venda", "Valor Líquido", "Valor Liquido"],
        ["venda", "fatur", "liquido", "líquido"]
    )

    col_produto = _sp_coluna(
        base_pesquisa,
        ["Produto", "Descrição", "Descricao", "Embalagem", "Nome Produto", "Produto Descrição", "Produto Descricao"],
        ["produto", "descr", "embalagem"]
    )

    col_marca = _sp_coluna(
        base_pesquisa,
        ["Marca", "Marca Produto", "Produto Marca"],
        ["marca"]
    )

    col_itens = _sp_coluna(
        base_pesquisa,
        ["Itens", "Item", "Quantidade", "Qtd", "QTD", "Qtde", "Unidades"],
        ["itens", "item", "qtd", "quant", "unid"]
    )

    if not col_venda:
        st.error("Não encontrei a coluna de faturamento/venda na VENDA_FINAL_TESTE.")
        st.write("Colunas encontradas:", base_pesquisa.columns.tolist())
        st.stop()

    base_pesquisa["Faturamento_SIM"] = _sp_numero(base_pesquisa[col_venda])

    if col_itens:
        base_pesquisa["Qtd_SIM"] = _sp_numero(base_pesquisa[col_itens])
    else:
        base_pesquisa["Qtd_SIM"] = 0

    if col_ean:
        base_pesquisa["EAN_SIM"] = (
            base_pesquisa[col_ean]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
        )
    else:
        base_pesquisa["EAN_SIM"] = ""

    if col_marca:
        base_pesquisa["Marca_Pesquisa"] = (
            base_pesquisa[col_marca]
            .astype(str)
            .str.strip()
            .str.upper()
        )
    else:
        base_pesquisa["Marca_Pesquisa"] = ""

    if col_ean and isinstance(df, pd.DataFrame) and "EAN" in df.columns:
        cadastro = df.copy()
        cadastro["EAN_SIM"] = (
            cadastro["EAN"]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
        )

        col_marca_df = _sp_coluna(
            cadastro,
            ["Marca", "Marca Produto", "Produto Marca"],
            ["marca"]
        )

        if col_marca_df:
            marca_ref = (
                cadastro[["EAN_SIM", col_marca_df]]
                .dropna()
                .drop_duplicates("EAN_SIM")
                .rename(columns={col_marca_df: "Marca_Cadastro"})
            )

            base_pesquisa = base_pesquisa.merge(
                marca_ref,
                on="EAN_SIM",
                how="left"
            )

            base_pesquisa["Marca_Pesquisa"] = np.where(
                base_pesquisa["Marca_Pesquisa"].astype(str).str.strip().isin(["", "NAN", "NONE"]),
                base_pesquisa["Marca_Cadastro"].astype(str).str.upper(),
                base_pesquisa["Marca_Pesquisa"]
            )

    if col_produto:
        base_pesquisa["Produto_Base_SIM"] = base_pesquisa[col_produto].astype(str)

        base_pesquisa["Marca_Pesquisa"] = np.where(
            base_pesquisa["Produto_Base_SIM"].astype(str).str.strip().ne(""),
            base_pesquisa["Produto_Base_SIM"].apply(_sp_marca),
            base_pesquisa["Marca_Pesquisa"]
        )
    else:
        base_pesquisa["Produto_Base_SIM"] = ""

    base_pesquisa["Marca_Pesquisa"] = (
        base_pesquisa["Marca_Pesquisa"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    base_pesquisa = base_pesquisa[
        (base_pesquisa["Marca_Pesquisa"].astype(str).str.len() > 0)
        & (~base_pesquisa["Marca_Pesquisa"].isin(["NAN", "NONE", "SEM MARCA"]))
        & (base_pesquisa["Faturamento_SIM"] > 0)
    ].copy()

    if base_pesquisa.empty:
        st.warning("Não foi possível montar marcas válidas pela VENDA_FINAL_TESTE.")
        st.stop()

    faturamento_total = float(base_pesquisa["Faturamento_SIM"].sum())

    ranking = (
        base_pesquisa
        .groupby("Marca_Pesquisa", dropna=False)
        .agg(
            Faturamento_Mensal=("Faturamento_SIM", "sum"),
            Qtd_Vendida=("Qtd_SIM", "sum"),
            SKUs=("EAN_SIM", "nunique"),
            Produtos_Exemplo=("Produto_Base_SIM", lambda x: " | ".join(pd.Series(x).dropna().astype(str).head(3).tolist()))
        )
        .reset_index()
        .rename(columns={"Marca_Pesquisa": "Marca"})
    )

    ranking["Participacao_%"] = (
        ranking["Faturamento_Mensal"] / faturamento_total * 100
        if faturamento_total > 0
        else 0
    )

    ranking = ranking.sort_values("Faturamento_Mensal", ascending=False).reset_index(drop=True)

    marcas_por_dia = 380

    dias_semana = [
        "Segunda-feira",
        "Terça-feira",
        "Quarta-feira",
        "Quinta-feira",
        "Sexta-feira",
        "Sábado",
        "Domingo"
    ]

    total_planejado = marcas_por_dia * len(dias_semana)

    selecionado = ranking.head(total_planejado).copy()

    selecionado["Posição Geral"] = range(1, len(selecionado) + 1)

    selecionado["Dia da Semana"] = [
        dias_semana[min(i // marcas_por_dia, len(dias_semana) - 1)]
        for i in range(len(selecionado))
    ]

    selecionado["Ordem no Dia"] = (
        selecionado
        .groupby("Dia da Semana")
        .cumcount()
        + 1
    )

    selecionado = selecionado[
        selecionado["Ordem no Dia"] <= marcas_por_dia
    ].copy()

    if len(selecionado) < total_planejado:
        st.info(
            f"Foram geradas {len(selecionado):,} pesquisas no total, separadas por faturamento em blocos de até {marcas_por_dia} por dia.".replace(",", ".")
        )

    faturamento_coberto = float(selecionado["Faturamento_Mensal"].sum())

    participacao_coberta = (
        faturamento_coberto / faturamento_total * 100
        if faturamento_total > 0
        else 0
    )

    k1, k2, k3, k4 = st.columns(4)

    k1.metric("Marcas por dia", marcas_por_dia)
    k2.metric("Total semanal", f"{len(selecionado):,}".replace(",", "."))
    k3.metric("Faturamento coberto", moeda_br(faturamento_coberto))
    k4.metric("Participação mensal", percentual_br(participacao_coberta))

    st.markdown("### 📅 Distribuição semanal")

    resumo_dia = (
        selecionado
        .groupby("Dia da Semana")
        .agg(
            Qtd_Marcas=("Marca", "count"),
            Faturamento_Coberto=("Faturamento_Mensal", "sum"),
            Participacao_Mensal=("Participacao_%", "sum")
        )
        .reset_index()
    )

    resumo_dia["Dia da Semana"] = pd.Categorical(
        resumo_dia["Dia da Semana"],
        categories=dias_semana,
        ordered=True
    )

    resumo_dia = resumo_dia.sort_values("Dia da Semana")

    resumo_exibir = resumo_dia.copy()
    resumo_exibir["Faturamento_Coberto"] = resumo_exibir["Faturamento_Coberto"].apply(moeda_br)
    resumo_exibir["Participacao_Mensal"] = resumo_exibir["Participacao_Mensal"].apply(percentual_br)

    st.dataframe(
        resumo_exibir,
        use_container_width=True,
        height=280
    )

    fig = px.bar(
        resumo_dia,
        x="Dia da Semana",
        y="Faturamento_Coberto",
        text="Qtd_Marcas",
        title="Faturamento coberto por dia de pesquisa"
    )

    fig.update_traces(textposition="outside")
    fig.update_layout(
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 🔎 Lista operacional de marcas para pesquisar")

    filtro_dia = st.selectbox(
        "Filtrar dia da semana",
        ["Todos"] + dias_semana,
        index=0,
        key="filtro_dia_sugestao_pesquisa"
    )

    tabela = selecionado.copy()

    if filtro_dia != "Todos":
        tabela = tabela[tabela["Dia da Semana"] == filtro_dia].copy()

    tabela = tabela[
        [
            "Dia da Semana",
            "Ordem no Dia",
            "Posição Geral",
            "Marca",
            "Faturamento_Mensal",
            "Participacao_%",
            "Qtd_Vendida",
            "SKUs",
            "Produtos_Exemplo"
        ]
    ].copy()

    tabela = tabela.rename(
        columns={
            "Faturamento_Mensal": "Faturamento Mensal",
            "Participacao_%": "Participação no Faturamento",
            "Qtd_Vendida": "Qtd Vendida",
            "Produtos_Exemplo": "Produtos Exemplo"
        }
    )

    tabela_exibir = tabela.copy()
    tabela_exibir["Faturamento Mensal"] = tabela_exibir["Faturamento Mensal"].apply(moeda_br)
    tabela_exibir["Participação no Faturamento"] = tabela_exibir["Participação no Faturamento"].apply(percentual_br)
    tabela_exibir["Qtd Vendida"] = tabela_exibir["Qtd Vendida"].apply(numero_br)

    st.dataframe(
        tabela_exibir,
        use_container_width=True,
        height=560
    )

    csv_pesquisa = (
        tabela_exibir
        .to_csv(index=False, sep=";")
        .encode("utf-8-sig")
    )

    st.download_button(
        "📥 Exportar sugestão de pesquisa",
        csv_pesquisa,
        "sugestao_pesquisa_380_marcas_por_dia.csv",
        "text/csv",
        key="exportar_sugestao_pesquisa"
    )

    st.stop()



# --------------------------------------------------
# PÁGINA DE DIAGNÓSTICO
# --------------------------------------------------

if pagina == "🧪 Diagnóstico":

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">Diagnóstico Técnico</div>
            <h1>🧪 Diagnóstico de Dados</h1>
            <p>Compare o que está rodando no localhost e no Streamlit Cloud.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.info(
        "Esta página ajuda a identificar se o online está lendo arquivos, pastas ou bases diferentes do localhost."
    )

    st.metric(
        "Versão do App",
        VERSAO_APP if "VERSAO_APP" in globals() else "sem versão"
    )

    st.write(
        "**Diretório atual:**",
        os.getcwd()
    )

    st.markdown("### Arquivos e pastas na raiz do projeto")

    try:

        itens_raiz = []

        for item in sorted(Path(".").iterdir()):

            itens_raiz.append(
                {
                    "Nome": item.name,
                    "Tipo": "Pasta" if item.is_dir() else "Arquivo",
                    "Tamanho KB": round(item.stat().st_size / 1024, 2) if item.is_file() else "",
                    "Modificado": datetime.fromtimestamp(
                        item.stat().st_mtime
                    ).strftime("%d/%m/%Y %H:%M:%S")
                }
            )

        st.dataframe(
            pd.DataFrame(itens_raiz),
            use_container_width=True,
            height=320
        )

    except Exception as erro:

        st.error(
            f"Erro ao listar raiz do projeto: {erro}"
        )

    st.markdown("### Arquivos nas pastas de dados")

    try:

        pastas = [
            "VENDA_TESTE",
            "VENDA_FINAL_TESTE",
            "VENDA_TESTE_FINAL",
            "COMPRA_TESTE",
            "ESTOQUE_TESTE"
        ]

        registros = []

        for pasta in pastas:

            pasta_path = Path(pasta)

            if not pasta_path.exists():

                registros.append(
                    {
                        "Pasta": pasta,
                        "Arquivo": "PASTA NÃO ENCONTRADA",
                        "Tamanho KB": "",
                        "Modificado": ""
                    }
                )

            else:

                arquivos = list(pasta_path.glob("*"))

                if not arquivos:

                    registros.append(
                        {
                            "Pasta": pasta,
                            "Arquivo": "PASTA VAZIA",
                            "Tamanho KB": "",
                            "Modificado": ""
                        }
                    )

                for arquivo in sorted(arquivos):

                    if arquivo.is_file():

                        registros.append(
                            {
                                "Pasta": pasta,
                                "Arquivo": arquivo.name,
                                "Tamanho KB": round(arquivo.stat().st_size / 1024, 2),
                                "Modificado": datetime.fromtimestamp(
                                    arquivo.stat().st_mtime
                                ).strftime("%d/%m/%Y %H:%M:%S")
                            }
                        )

        st.dataframe(
            pd.DataFrame(registros),
            use_container_width=True,
            height=360
        )

    except Exception as erro:

        st.error(
            f"Erro ao listar pastas de dados: {erro}"
        )

    st.markdown("### Conferência do arquivo principal")

    try:
        arquivo_principal = Path("Analise_Pricing.xlsx")
        if arquivo_principal.exists():
            st.write(
                {
                    "Arquivo": "Analise_Pricing.xlsx",
                    "Tamanho_KB": round(arquivo_principal.stat().st_size / 1024, 2),
                    "Modificado": datetime.fromtimestamp(
                        arquivo_principal.stat().st_mtime
                    ).strftime("%d/%m/%Y %H:%M:%S")
                }
            )
        else:
            st.error("Analise_Pricing.xlsx não encontrado.")
    except Exception as erro:
        st.error(f"Erro ao conferir Analise_Pricing.xlsx: {erro}")


    st.markdown("### Diagnóstico da VENDA_FINAL_TESTE")

    try:
        candidatos_venda_final = []

        for ext in ["*.xls", "*.xlsx", "*.xlsm", "*.csv"]:
            for arquivo in Path(".").rglob(ext):
                if arquivo.name.lower() != "analise_pricing.xlsx":
                    candidatos_venda_final.append(
                        {
                            "Arquivo": str(arquivo),
                            "Tamanho_KB": round(arquivo.stat().st_size / 1024, 2),
                            "Pasta": str(arquivo.parent)
                        }
                    )

        st.dataframe(
            pd.DataFrame(candidatos_venda_final),
            use_container_width=True,
            height=240
        )

        if "ERROS_CARGA_VENDA_FINAL_TESTE" in globals() and ERROS_CARGA_VENDA_FINAL_TESTE:
            st.warning("Alguns arquivos Excel/CSV foram encontrados, mas deram erro na leitura.")
            st.dataframe(
                pd.DataFrame(ERROS_CARGA_VENDA_FINAL_TESTE),
                use_container_width=True,
                height=240
            )

    except Exception as erro:
        st.error(f"Erro no diagnóstico da VENDA_FINAL_TESTE: {erro}")


    st.markdown("### Bases carregadas")

    resumo_bases = pd.DataFrame(
        [
            {
                "Base": "df / Analise_Pricing.xlsx",
                "Linhas": len(df) if isinstance(df, pd.DataFrame) else 0,
                "Colunas": len(df.columns) if isinstance(df, pd.DataFrame) else 0
            },
            {
                "Base": "historico / VENDA_TESTE",
                "Linhas": len(historico) if isinstance(historico, pd.DataFrame) else 0,
                "Colunas": len(historico.columns) if isinstance(historico, pd.DataFrame) else 0
            },
            {
                "Base": "compra",
                "Linhas": len(compra) if isinstance(compra, pd.DataFrame) else 0,
                "Colunas": len(compra.columns) if isinstance(compra, pd.DataFrame) else 0
            },
            {
                "Base": "venda_rede / VENDA_FINAL_TESTE",
                "Linhas": len(venda_rede) if isinstance(venda_rede, pd.DataFrame) else 0,
                "Colunas": len(venda_rede.columns) if isinstance(venda_rede, pd.DataFrame) else 0
            },
            {
                "Base": "estoque / ESTOQUE_TESTE",
                "Linhas": len(estoque) if isinstance(estoque, pd.DataFrame) else 0,
                "Colunas": len(estoque.columns) if isinstance(estoque, pd.DataFrame) else 0
            },
            {
                "Base": f"simulacao_global / origem: {origem_simulacao_global if 'origem_simulacao_global' in globals() else 'não definida'}",
                "Linhas": len(simulacao_global) if "simulacao_global" in globals() and isinstance(simulacao_global, pd.DataFrame) else 0,
                "Colunas": len(simulacao_global.columns) if "simulacao_global" in globals() and isinstance(simulacao_global, pd.DataFrame) else 0
            }
        ]
    )

    st.dataframe(
        resumo_bases,
        use_container_width=True,
        height=260
    )

    st.markdown("### Top 30 da simulação")

    if (
        "simulacao_global" in globals()
        and isinstance(simulacao_global, pd.DataFrame)
        and not simulacao_global.empty
    ):

        cols_amostra = [
            c for c in [
                "EAN",
                "Produto_Simulador",
                "Produto",
                "Qtd_Vendida_Mes_Anterior",
                "Preco_Atual",
                "Preco_Sugerido_Mercado",
                "Ganho_Unitario",
                "Ganho_Potencial_Simulador"
            ]
            if c in simulacao_global.columns
        ]

        amostra = simulacao_global[cols_amostra].copy()

        if "Ganho_Potencial_Simulador" in amostra.columns:

            amostra["_ordem"] = pd.to_numeric(
                amostra["Ganho_Potencial_Simulador"],
                errors="coerce"
            )

            amostra = (
                amostra
                .sort_values("_ordem", ascending=False)
                .drop(columns=["_ordem"])
                .head(30)
            )

        st.dataframe(
            amostra,
            use_container_width=True,
            height=420
        )

    else:

        st.warning(
            "simulacao_global está vazia ou não foi criada."
        )

    st.stop()



# --------------------------------------------------
# SIMULADOR INTELIGENTE DE PRICING
# --------------------------------------------------

if pagina == "📈 Simulador Inteligente":

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">Pricing Intelligence</div>
            <h1>📈 Simulador Inteligente de Pricing</h1>
            <p>Simule preço, margem, competitividade e impacto financeiro usando automaticamente os dados da base pelo EAN/código de barras.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    base_sim = df_filtrado.copy()
    base_sim = propagar_ganho_potencial(base_sim)

    if "EAN" in base_sim.columns:
        base_sim["EAN"] = (
            base_sim["EAN"]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
        )

    # --------------------------------------------------
    # FUNÇÕES AUXILIARES DO SIMULADOR
    # --------------------------------------------------

    def _num_sim(valor, padrao=0.0):
        try:
            if valor is None:
                return padrao

            if str(valor).strip().lower() in ["", "none", "nan", "nat"]:
                return padrao

            v = pd.to_numeric(valor, errors="coerce")

            if pd.isna(v):
                return padrao

            return float(v)

        except Exception:
            return padrao

    def _primeiro_valor_linha(linha, colunas, padrao=0.0):
        for col in colunas:
            if col in linha.index:
                v = _num_sim(linha.get(col), None)
                if v is not None and not pd.isna(v) and float(v) != 0:
                    return float(v)
        return float(padrao)

    def _buscar_coluna(base, opcoes):
        for col in opcoes:
            if col in base.columns:
                return col
        return None

    def _buscar_coluna_flex(base, exatos, contem=None):
        if not isinstance(base, pd.DataFrame) or base.empty:
            return None

        contem = contem or []

        for alvo in exatos:
            for col in base.columns:
                if str(col).strip().lower() == str(alvo).strip().lower():
                    return col

        for termo in contem:
            termo = str(termo).lower()
            for col in base.columns:
                if termo in str(col).lower():
                    return col

        return None

    def _num_serie_sim(serie):
        if isinstance(serie, pd.Series):
            s = (
                serie.astype(str)
                .str.strip()
                .str.replace("R$", "", regex=False)
                .str.replace("%", "", regex=False)
                .str.replace(" ", "", regex=False)
            )

            tem_virgula = s.str.contains(",", regex=False)

            s_br = (
                s[tem_virgula]
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
            )

            s_us = (
                s[~tem_virgula]
                .str.replace(",", "", regex=False)
            )

            out = pd.Series(index=serie.index, dtype="float64")
            out.loc[s_br.index] = pd.to_numeric(s_br, errors="coerce")
            out.loc[s_us.index] = pd.to_numeric(s_us, errors="coerce")

            return out

        return pd.to_numeric(serie, errors="coerce")

    def _normalizar_ean_sim(valor):
        return str(valor).replace(".0", "").strip()

    def _tipo_loja_sim(linha):
        texto = (
            str(linha.get("Farmácia", ""))
            + " "
            + str(linha.get("Rede", ""))
            + " "
            + str(linha.get("Nome Fantasia", ""))
        ).upper()

        if (
            "ZANOL" in texto
            or "THOMAZ" in texto
            or "TRIANGULO" in texto
            or "TRIÂNGULO" in texto
        ):
            return "REDE"

        return "CONCORRENTE"

    def _preparar_historico_simulador(base):
        if not isinstance(base, pd.DataFrame) or base.empty:
            return pd.DataFrame()

        h = base.copy()
        h.columns = h.columns.astype(str).str.strip()

        col_ean = _buscar_coluna_flex(
            h,
            ["EAN", "EAN (GTIN)", "GTIN", "Código de Barras", "Codigo de Barras"],
            ["ean", "gtin", "barras"]
        )

        col_preco = _buscar_coluna_flex(
            h,
            ["Preço (R$)", "Preco (R$)", "Preço", "Preco", "Valor", "Valor Unitário", "Valor Unitario"],
            ["preço", "preco", "valor"]
        )

        col_data = _buscar_coluna_flex(
            h,
            ["Data Emissão", "Data Emissao", "Data", "Dt Emissão", "Dt Emissao"],
            ["data", "emissão", "emissao"]
        )

        if not col_ean or not col_preco:
            return pd.DataFrame()

        h["EAN_SIM"] = h[col_ean].apply(_normalizar_ean_sim)
        h["Preco_SIM"] = _num_serie_sim(h[col_preco])

        if col_data:
            h["Data_SIM"] = pd.to_datetime(
                h[col_data],
                errors="coerce",
                dayfirst=True
            )
        else:
            h["Data_SIM"] = pd.NaT

        if "Farmácia" not in h.columns:
            h["Farmácia"] = ""

        if "Rede" not in h.columns:
            h["Rede"] = ""

        if "Nome Fantasia" not in h.columns:
            h["Nome Fantasia"] = ""

        if "Produto" not in h.columns:
            h["Produto"] = ""

        h["Tipo_Loja_SIM"] = h.apply(
            _tipo_loja_sim,
            axis=1
        )

        h = h[
            (h["EAN_SIM"].astype(str).str.len() > 0)
            & (h["Preco_SIM"] > 0)
            & (h["Preco_SIM"] <= 5000)
        ].copy()

        return h

    def _preparar_venda_final_simulador(base):
        if not isinstance(base, pd.DataFrame) or base.empty:
            return pd.DataFrame()

        v = base.copy()
        v.columns = v.columns.astype(str).str.strip()

        col_ean = _buscar_coluna_flex(
            v,
            [
                "EAN",
                "EAN (GTIN)",
                "GTIN",
                "Cód. Barras/Etiq.",
                "Cod. Barras/Etiq.",
                "Código de Barras",
                "Codigo de Barras"
            ],
            ["ean", "gtin", "barras", "etiq"]
        )

        col_itens = _buscar_coluna_flex(
            v,
            ["Itens", "Item", "Quantidade", "Qtd", "QTD", "Qtde", "Unidades"],
            ["itens", "item", "qtd", "quant", "unid"]
        )

        col_venda = _buscar_coluna_flex(
            v,
            ["Venda", "Valor Venda", "Faturamento", "Valor Total", "Total Venda"],
            ["venda", "fatur"]
        )

        col_custo = _buscar_coluna_flex(
            v,
            ["Custo", "Custo Médio", "Custo Medio", "Valor Custo", "Custo Total"],
            ["custo"]
        )

        if not col_ean:
            return pd.DataFrame()

        v["EAN_SIM"] = v[col_ean].apply(_normalizar_ean_sim)

        if col_itens:
            v["Itens_SIM"] = _num_serie_sim(v[col_itens])
        else:
            v["Itens_SIM"] = np.nan

        if col_venda:
            v["Venda_SIM"] = _num_serie_sim(v[col_venda])
        else:
            v["Venda_SIM"] = np.nan

        if col_custo:
            v["Custo_SIM"] = _num_serie_sim(v[col_custo])
        else:
            v["Custo_SIM"] = np.nan

        return v

    def _preparar_estoque_simulador(base):
        if not isinstance(base, pd.DataFrame) or base.empty:
            return pd.DataFrame()

        e = base.copy()
        e.columns = e.columns.astype(str).str.strip()

        col_ean = _buscar_coluna_flex(
            e,
            [
                "EAN",
                "EAN (GTIN)",
                "GTIN",
                "Cód. Barras/Etiq.",
                "Cod. Barras/Etiq.",
                "Código de Barras",
                "Codigo de Barras"
            ],
            ["ean", "gtin", "barras", "etiq"]
        )

        col_custo = _buscar_coluna_flex(
            e,
            [
                "Custo",
                "Custo Médio",
                "Custo Medio",
                "Preço Custo",
                "Preco Custo",
                "Valor Custo",
                "CMV"
            ],
            ["custo", "cmv"]
        )

        if not col_ean or not col_custo:
            return pd.DataFrame()

        e["EAN_SIM"] = e[col_ean].apply(_normalizar_ean_sim)
        e["Custo_Estoque_SIM"] = _num_serie_sim(e[col_custo])

        e = e[
            (e["EAN_SIM"].astype(str).str.len() > 0)
            & (e["Custo_Estoque_SIM"] > 0)
            & (e["Custo_Estoque_SIM"] <= 5000)
        ].copy()

        return e

    def _dados_preco_atual_sim(ean, hist_preparado, venda_final_preparada):
        ean = _normalizar_ean_sim(ean)

        if isinstance(hist_preparado, pd.DataFrame) and not hist_preparado.empty:
            rede = hist_preparado[
                (hist_preparado["EAN_SIM"] == ean)
                & (hist_preparado["Tipo_Loja_SIM"] == "REDE")
            ].copy()

            if not rede.empty:
                if rede["Data_SIM"].notna().any():
                    rede = rede.sort_values("Data_SIM", ascending=False)

                linha = rede.iloc[0]

                return (
                    float(linha["Preco_SIM"]),
                    "VENDA_TESTE - preço da rede na data mais recente",
                    f"{linha.get('Farmácia', '')} | {linha.get('Rede', '')}"
                )

        if isinstance(venda_final_preparada, pd.DataFrame) and not venda_final_preparada.empty:
            vf = venda_final_preparada[
                venda_final_preparada["EAN_SIM"] == ean
            ].copy()

            if not vf.empty and vf["Itens_SIM"].sum() > 0 and vf["Venda_SIM"].sum() > 0:
                return (
                    float(vf["Venda_SIM"].sum() / vf["Itens_SIM"].sum()),
                    "VENDA_FINAL_TESTE - preço médio Venda / Itens",
                    ""
                )

        return 0.0, "Preço atual não localizado", ""

    def _dados_custo_sim(ean, estoque_preparado, venda_final_preparada):
        ean = _normalizar_ean_sim(ean)

        if isinstance(estoque_preparado, pd.DataFrame) and not estoque_preparado.empty:
            est = estoque_preparado[
                estoque_preparado["EAN_SIM"] == ean
            ].copy()

            if not est.empty:
                custo = est["Custo_Estoque_SIM"].dropna().mean()

                if pd.notna(custo) and custo > 0:
                    return float(custo), "ESTOQUE_TESTE"

        if isinstance(venda_final_preparada, pd.DataFrame) and not venda_final_preparada.empty:
            vf = venda_final_preparada[
                venda_final_preparada["EAN_SIM"] == ean
            ].copy()

            if not vf.empty:
                if vf["Itens_SIM"].sum() > 0 and vf["Custo_SIM"].sum() > 0:
                    custo = vf["Custo_SIM"].sum() / vf["Itens_SIM"].sum()

                    if pd.notna(custo) and custo > 0:
                        return float(custo), "VENDA_FINAL_TESTE - Custo / Itens"

                custo = vf["Custo_SIM"].dropna().mean()

                if pd.notna(custo) and custo > 0:
                    return float(custo), "VENDA_FINAL_TESTE - custo médio"

        return 0.0, "Custo não localizado"

    def _qtd_vendida_mes_anterior_sim(ean, venda_final_preparada):
        """
        Quantidade vendida do mês anterior pela VENDA_FINAL_TESTE.
        Soma a coluna Itens do produto/EAN.
        """

        ean = _normalizar_ean_sim(ean)

        if not isinstance(venda_final_preparada, pd.DataFrame) or venda_final_preparada.empty:
            return 1.0

        vf = venda_final_preparada[
            venda_final_preparada["EAN_SIM"] == ean
        ].copy()

        if vf.empty or "Itens_SIM" not in vf.columns:
            return 1.0

        qtd = vf["Itens_SIM"].dropna().sum()

        if pd.notna(qtd) and qtd > 0:
            return float(qtd)

        return 1.0

    def _qtd_estoque_produto_sim(ean, estoque_base):
        """
        Quantidade em estoque pela ESTOQUE_TESTE.
        O valor vem preenchido, mas o usuário pode simular alterando o campo.
        """

        ean = _normalizar_ean_sim(ean)

        if not isinstance(estoque_base, pd.DataFrame) or estoque_base.empty:
            return 0.0

        est = estoque_base.copy()
        est.columns = est.columns.astype(str).str.strip()

        col_ean = _buscar_coluna_flex(
            est,
            [
                "EAN",
                "EAN (GTIN)",
                "GTIN",
                "Cód. Barras/Etiq.",
                "Cod. Barras/Etiq.",
                "Código de Barras",
                "Codigo de Barras"
            ],
            ["ean", "gtin", "barras", "etiq"]
        )

        col_qtd = _buscar_coluna_flex(
            est,
            [
                "Estoque",
                "Qtd Estoque",
                "Qtde Estoque",
                "Quantidade Estoque",
                "Saldo",
                "Saldo Estoque",
                "Disponível",
                "Disponivel",
                "Quantidade",
                "Qtd",
                "Qtde"
            ],
            ["estoque", "saldo", "dispon", "qtd", "qtde", "quant"]
        )

        if not col_ean or not col_qtd:
            return 0.0

        est["EAN_SIM"] = est[col_ean].apply(_normalizar_ean_sim)
        est["Qtd_Estoque_SIM"] = _num_serie_sim(est[col_qtd])

        est = est[
            est["EAN_SIM"] == ean
        ].copy()

        if est.empty:
            return 0.0

        qtd = est["Qtd_Estoque_SIM"].dropna().sum()

        if pd.notna(qtd) and qtd > 0:
            return float(qtd)

        return 0.0

    def _concorrentes_sim(ean, hist_preparado):
        ean = _normalizar_ean_sim(ean)

        if not isinstance(hist_preparado, pd.DataFrame) or hist_preparado.empty:
            return pd.DataFrame()

        conc = hist_preparado[
            (hist_preparado["EAN_SIM"] == ean)
            & (hist_preparado["Tipo_Loja_SIM"] == "CONCORRENTE")
        ].copy()

        if conc.empty:
            return pd.DataFrame()

        conc = conc.sort_values(
            ["Preco_SIM", "Data_SIM"],
            ascending=[True, False]
        )

        return conc

    def _escolher_preco_concorrente_sim(concorrentes, custo, cenario):
        if not isinstance(concorrentes, pd.DataFrame) or concorrentes.empty:
            return 0.0, 0.0, "", "", pd.DataFrame()

        conc = concorrentes.copy()
        conc["Margem_vs_Custo"] = conc["Preco_SIM"] - custo

        menor = conc.iloc[0]
        menor_preco = float(menor["Preco_SIM"])
        menor_legenda = f"{menor.get('Farmácia', '')} | {menor.get('Rede', '')}"

        cenario = str(cenario).upper()

        if cenario == "COMPETITIVO":
            elegiveis = conc[conc["Margem_vs_Custo"] >= 0].copy()

            if not elegiveis.empty:
                ref = elegiveis.iloc[0]
                return (
                    float(ref["Preco_SIM"]),
                    menor_preco,
                    menor_legenda,
                    f"{ref.get('Farmácia', '')} | {ref.get('Rede', '')}",
                    conc
                )

            return (
                menor_preco,
                menor_preco,
                menor_legenda,
                f"{menor.get('Farmácia', '')} | {menor.get('Rede', '')} | margem negativa",
                conc
            )

        if cenario == "CONSERVADOR":
            elegiveis = conc[conc["Margem_vs_Custo"] >= 0].copy()

            if not elegiveis.empty:
                ref = elegiveis.iloc[0]
                return (
                    float(ref["Preco_SIM"]),
                    menor_preco,
                    menor_legenda,
                    f"{ref.get('Farmácia', '')} | {ref.get('Rede', '')}",
                    conc
                )

            return (
                max(float(custo), menor_preco),
                menor_preco,
                menor_legenda,
                "Preço ajustado para não ficar abaixo do custo",
                conc
            )

        if cenario == "AGRESSIVO":
            return (
                menor_preco,
                menor_preco,
                menor_legenda,
                f"{menor.get('Farmácia', '')} | {menor.get('Rede', '')}",
                conc
            )

        return (
            menor_preco,
            menor_preco,
            menor_legenda,
            f"{menor.get('Farmácia', '')} | {menor.get('Rede', '')}",
            conc
        )

    hist_sim_preparado = _preparar_historico_simulador(historico)
    venda_final_sim_preparada = _preparar_venda_final_simulador(venda_rede)
    estoque_sim_preparado = _preparar_estoque_simulador(estoque)

    # --------------------------------------------------
    # FILTRO POR CÓDIGO DE BARRAS / EAN
    # --------------------------------------------------

    ean_digitado = "78911222"

    # Se o usuário já filtrou no menu lateral por EAN/produto, aproveita automaticamente.
    try:
        busca_global = str(busca).strip()
    except Exception:
        busca_global = ""

    if busca_global and busca_global.isdigit():
        ean_digitado = busca_global
    elif not busca_global:
        ean_digitado = "78911222"

    col_ean_base = "EAN" if "EAN" in base_sim.columns else None

    ean_input = st.text_input(
        "Código de barras / EAN para simular",
        value=ean_digitado,
        placeholder="Digite ou cole o EAN do produto",
        key="sim_ean_codigo_barras"
    )

    base_lookup = base_sim.copy()

    if ean_input and col_ean_base:
        ean_limpo = (
            str(ean_input)
            .replace(".0", "")
            .strip()
        )

        ean_series_filtro = (
            base_lookup[col_ean_base]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
        )

        base_lookup = base_lookup[
            ean_series_filtro.str.startswith(ean_limpo, na=False)
            | ean_series_filtro.str.contains(ean_limpo, na=False)
        ].copy()

        if base_lookup.empty:
            st.warning(
                "Nenhum produto encontrado para esse EAN/código de barras dentro dos filtros atuais."
            )
            st.stop()

    col_produto_sim = "Descricao_Unica" if "Descricao_Unica" in base_lookup.columns else "Produto"

    if col_produto_sim in base_lookup.columns and not base_lookup.empty:

        opcoes_produto = (
            base_lookup[col_produto_sim]
            .dropna()
            .astype(str)
            .sort_values()
            .unique()
            .tolist()
        )

        # Se houver apenas um produto pelo EAN, ele já fica selecionado automaticamente.
        produto_selecionado_sim = st.selectbox(
            "Selecione o produto para simular",
            opcoes_produto,
            index=0,
            key="produto_simulador_inteligente"
        )

        item_sim = base_lookup[
            base_lookup[col_produto_sim].astype(str) == str(produto_selecionado_sim)
        ].head(1).copy()

        if not item_sim.empty:

            item = item_sim.iloc[0]

            ean_sim = str(item.get("EAN", "")).replace(".0", "").strip()

            # --------------------------------------------------
            # DADOS AUTOMÁTICOS DO SIMULADOR
            # --------------------------------------------------

            preco_atual_padrao, origem_preco_atual, legenda_preco_atual = _dados_preco_atual_sim(
                ean_sim,
                hist_sim_preparado,
                venda_final_sim_preparada
            )

            custo_padrao, origem_custo = _dados_custo_sim(
                ean_sim,
                estoque_sim_preparado,
                venda_final_sim_preparada
            )

            qtd_padrao = _qtd_vendida_mes_anterior_sim(
                ean_sim,
                venda_final_sim_preparada
            )

            qtd_estoque_padrao = _qtd_estoque_produto_sim(
                ean_sim,
                estoque
            )

            concorrentes_produto_sim = _concorrentes_sim(
                ean_sim,
                hist_sim_preparado
            )

            (
                preco_sugerido_padrao,
                menor_concorrente_padrao,
                legenda_menor_concorrente,
                legenda_preco_sugerido,
                pesquisas_calculo_sim
            ) = _escolher_preco_concorrente_sim(
                concorrentes_produto_sim,
                custo_padrao,
                "Competitivo"
            )

            if not preco_sugerido_padrao or preco_sugerido_padrao <= 0:
                preco_sugerido_padrao = preco_atual_padrao

            st.markdown("### 🧾 Produto carregado automaticamente")

            info1, info2, info3, info4 = st.columns(4)

            info1.metric("EAN", ean_sim if ean_sim else "Não informado")

            info2.metric("Preço atual base", moeda_br(preco_atual_padrao))
            if legenda_preco_atual:
                info2.caption(legenda_preco_atual)

            info3.metric("Menor concorrente", moeda_br(menor_concorrente_padrao))
            if legenda_menor_concorrente:
                info3.caption(legenda_menor_concorrente)

            info4.metric("Qtd mês base", numero_br(qtd_padrao))
            info4.caption("Venda do mês anterior")

            st.markdown("### 🎛️ Parâmetros da simulação")

            c1, c2, c3, c4 = st.columns(4)

            with c1:
                preco_atual = st.number_input(
                    "Preço atual",
                    min_value=0.0,
                    value=float(preco_atual_padrao if preco_atual_padrao is not None else 0),
                    step=0.10,
                    format="%.2f",
                    key=f"sim_preco_atual_{ean_sim}"
                )
                # legenda origem removida
                if legenda_preco_atual:
                    st.caption(legenda_preco_atual)

            with c2:
                novo_preco = st.number_input(
                    "Novo preço simulado",
                    min_value=0.0,
                    value=float(preco_sugerido_padrao if preco_sugerido_padrao is not None else (preco_atual_padrao if preco_atual_padrao is not None else 0)),
                    step=0.10,
                    format="%.2f",
                    key=f"sim_novo_preco_{ean_sim}"
                )
                if legenda_preco_sugerido:
                    st.caption(f"Referência: {legenda_preco_sugerido}")

            with c3:
                custo = st.number_input(
                    "Custo",
                    min_value=0.0,
                    value=float(custo_padrao if custo_padrao is not None else 0),
                    step=0.10,
                    format="%.2f",
                    key=f"sim_custo_{ean_sim}"
                )
                # legenda origem removida

            with c4:
                qtd_mes = st.number_input(
                    "Qtd vendida/mês",
                    min_value=0.0,
                    value=float(qtd_padrao if qtd_padrao is not None else 1),
                    step=1.0,
                    format="%.0f",
                    key=f"sim_qtd_mes_{ean_sim}"
                )

            c5, c6, c7, c8 = st.columns(4)

            with c5:
                menor_concorrente = st.number_input(
                    "Menor preço concorrente",
                    min_value=0.0,
                    value=float(menor_concorrente_padrao if menor_concorrente_padrao is not None else 0),
                    step=0.10,
                    format="%.2f",
                    key=f"sim_menor_concorrente_{ean_sim}"
                )
                if legenda_menor_concorrente:
                    st.caption(f"Concorrente: {legenda_menor_concorrente}")

            with c6:
                cenario = st.selectbox(
                    "Cenário",
                    [
                        "Competitivo",
                        "Conservador",
                        "Agressivo",
                        "Maximizar margem",
                        "Manual"
                    ],
                    index=0,
                    key=f"sim_cenario_{ean_sim}"
                )

            with c7:
                qtd_estoque = st.number_input(
                    "Qtd em estoque",
                    min_value=0.0,
                    value=float(qtd_estoque_padrao if qtd_estoque_padrao is not None else 0),
                    step=1.0,
                    format="%.0f",
                    key=f"sim_qtd_estoque_{ean_sim}"
                )
                st.caption("Estoque atual do produto")

            if cenario != "Manual":

                (
                    novo_preco_calc,
                    menor_concorrente_calc,
                    legenda_menor_concorrente_calc,
                    legenda_preco_sugerido_calc,
                    pesquisas_calculo_sim
                ) = _escolher_preco_concorrente_sim(
                    concorrentes_produto_sim,
                    custo,
                    cenario
                )

                if cenario == "Maximizar margem":
                    novo_preco_calc = preco_atual * 1.08

                if novo_preco_calc and novo_preco_calc > 0:
                    novo_preco = float(novo_preco_calc)

                if menor_concorrente_calc and menor_concorrente_calc > 0:
                    menor_concorrente = float(menor_concorrente_calc)

                with c8:
                    st.metric("Preço sugerido", moeda_br(novo_preco))
                    if legenda_preco_sugerido_calc:
                        st.caption(f"Referência: {legenda_preco_sugerido_calc}")

            lucro_atual_calc = preco_atual - custo
            lucro_novo_calc = novo_preco - custo

            margem_atual_calc = (lucro_atual_calc / preco_atual * 100) if preco_atual > 0 else 0
            margem_nova_calc = (lucro_novo_calc / novo_preco * 100) if novo_preco > 0 else 0

            dif_preco_rs = novo_preco - preco_atual
            dif_preco_perc = (dif_preco_rs / preco_atual * 100) if preco_atual > 0 else 0

            venda_atual = preco_atual * qtd_mes
            venda_nova = novo_preco * qtd_mes

            lucro_total_atual = lucro_atual_calc * qtd_mes
            lucro_total_novo = lucro_novo_calc * qtd_mes

            impacto_faturamento = venda_nova - venda_atual
            impacto_lucro = lucro_total_novo - lucro_total_atual
            impacto_anual = impacto_lucro * 12

            if menor_concorrente > 0:
                dif_vs_concorrente = novo_preco - menor_concorrente
                dif_vs_concorrente_perc = dif_vs_concorrente / menor_concorrente * 100
            else:
                dif_vs_concorrente = 0
                dif_vs_concorrente_perc = 0

            if menor_concorrente > 0 and novo_preco > menor_concorrente * 1.10:
                risco = "🔴 Alto risco competitivo"
            elif menor_concorrente > 0 and novo_preco > menor_concorrente * 1.03:
                risco = "🟡 Atenção competitiva"
            else:
                risco = "🟢 Seguro"

            st.markdown("### 📌 Resultado da simulação")

            k1, k2, k3, k4 = st.columns(4)

            k1.metric(
                "Diferença de preço",
                moeda_br(dif_preco_rs),
                percentual_br(dif_preco_perc)
            )

            k2.metric(
                "Margem simulada",
                percentual_br(margem_nova_calc),
                percentual_br(margem_nova_calc - margem_atual_calc)
            )

            k3.metric(
                "Impacto lucro/mês",
                moeda_br(impacto_lucro)
            )

            k4.metric(
                "Impacto lucro/ano",
                moeda_br(impacto_anual)
            )

            k5, k6, k7, k8 = st.columns(4)

            k5.metric(
                "Venda atual/mês",
                moeda_br(venda_atual)
            )

            k6.metric(
                "Venda simulada/mês",
                moeda_br(venda_nova)
            )

            k7.metric(
                "Dif. vs concorrente",
                moeda_br(dif_vs_concorrente),
                percentual_br(dif_vs_concorrente_perc)
            )

            k8.metric(
                "Risco",
                risco
            )

            st.markdown("### 📊 Comparativo visual")

            grafico_sim = pd.DataFrame(
                {
                    "Cenário": [
                        "Preço atual",
                        "Novo preço",
                        "Menor concorrente",
                        "Custo"
                    ],
                    "Valor": [
                        preco_atual,
                        novo_preco,
                        menor_concorrente,
                        custo
                    ]
                }
            )

            fig = px.bar(
                grafico_sim,
                x="Cenário",
                y="Valor",
                text="Valor",
                title="Comparação de preço, concorrência e custo"
            )

            fig.update_traces(
                texttemplate="R$ %{text:.2f}",
                textposition="outside"
            )

            fig.update_layout(
                height=420,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            st.markdown("### 📋 Resumo decisório")

            resumo_sim = pd.DataFrame(
                [
                    {
                        "Produto": item.get("Produto", produto_selecionado_sim),
                        "EAN": ean_sim,
                        "Preço Atual": moeda_br(preco_atual),
                        "Novo Preço": moeda_br(novo_preco),
                        "Custo": moeda_br(custo),
                        "Qtd Vendida/Mês": numero_br(qtd_mes),
                        "Qtd em Estoque": numero_br(qtd_estoque),
                        "Menor Concorrente": moeda_br(menor_concorrente),
                        "Margem Atual": percentual_br(margem_atual_calc),
                        "Margem Simulada": percentual_br(margem_nova_calc),
                        "Impacto Faturamento Mensal": moeda_br(impacto_faturamento),
                        "Impacto Lucro Mensal": moeda_br(impacto_lucro),
                        "Impacto Lucro Anual": moeda_br(impacto_anual),
                        "Risco Competitivo": risco
                    }
                ]
            )

            st.dataframe(
                resumo_sim,
                use_container_width=True,
                height=140
            )

            st.markdown("### 🔎 Pesquisas do produto utilizadas no cálculo")

            auditoria_sim = hist_sim_preparado[
                hist_sim_preparado["EAN_SIM"] == ean_sim
            ].copy() if isinstance(hist_sim_preparado, pd.DataFrame) and not hist_sim_preparado.empty else pd.DataFrame()

            if auditoria_sim.empty:

                st.warning(
                    "Não há pesquisas de preço para este produto na VENDA_TESTE."
                )

            else:

                auditoria_sim["Margem vs Custo"] = auditoria_sim["Preco_SIM"] - custo
                auditoria_sim["Referência no Cálculo"] = ""

                if isinstance(pesquisas_calculo_sim, pd.DataFrame) and not pesquisas_calculo_sim.empty:

                    menor_preco_calc = pesquisas_calculo_sim["Preco_SIM"].min()

                    auditoria_sim.loc[
                        auditoria_sim["Preco_SIM"] == menor_preco_calc,
                        "Referência no Cálculo"
                    ] = "Menor preço concorrente"

                    ref_preco_calc = novo_preco

                    auditoria_sim.loc[
                        auditoria_sim["Preco_SIM"] == ref_preco_calc,
                        "Referência no Cálculo"
                    ] = "Preço simulado"

                cols_auditoria = [
                    c for c in [
                        "Data_SIM",
                        "EAN_SIM",
                        "Produto",
                        "Farmácia",
                        "Nome Fantasia",
                        "Rede",
                        "Tipo_Loja_SIM",
                        "Preco_SIM",
                        "Margem vs Custo",
                        "Referência no Cálculo"
                    ]
                    if c in auditoria_sim.columns
                ]

                auditoria_exibir = auditoria_sim[cols_auditoria].copy()

                auditoria_exibir = auditoria_exibir.rename(
                    columns={
                        "Data_SIM": "Data Pesquisa",
                        "EAN_SIM": "EAN",
                        "Tipo_Loja_SIM": "Tipo Loja",
                        "Preco_SIM": "Preço Pesquisa"
                    }
                )

                if "Data Pesquisa" in auditoria_exibir.columns:
                    auditoria_exibir["Data Pesquisa"] = pd.to_datetime(
                        auditoria_exibir["Data Pesquisa"],
                        errors="coerce"
                    ).dt.strftime("%d/%m/%Y")

                for col_moeda in [
                    "Preço Pesquisa",
                    "Margem vs Custo"
                ]:
                    if col_moeda in auditoria_exibir.columns:
                        auditoria_exibir[col_moeda] = auditoria_exibir[col_moeda].apply(moeda_br)

                st.dataframe(
                    auditoria_exibir,
                    use_container_width=True,
                    height=360
                )

            csv_sim = (
                resumo_sim
                .to_csv(index=False, sep=";")
                .encode("utf-8-sig")
            )

            st.download_button(
                "📥 Exportar simulação",
                csv_sim,
                "simulacao_inteligente_pricing.csv",
                "text/csv",
                key=f"exportar_simulador_inteligente_{ean_sim}"
            )

    else:

        st.warning(
            "Não foi possível carregar produtos para simulação. Verifique se a base possui Produto ou Descricao_Unica."
        )

    st.stop()



# --------------------------------------------------
# DASHBOARD EXECUTIVO PREMIUM
# --------------------------------------------------

if pagina == "🏢 Dashboard Executivo":

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">Diretoria</div>
            <h1>🏢 Dashboard Executivo Premium</h1>
            <p>Resumo estratégico para tomada de decisão: riscos, oportunidades, margem e potencial de captura.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    base_exec = df_filtrado.copy()
    base_exec = propagar_ganho_potencial(base_exec)

    total_produtos = len(base_exec)

    ganho_total = 0
    if "Ganho_Potencial" in base_exec.columns:
        ganho_total = pd.to_numeric(
            base_exec["Ganho_Potencial"],
            errors="coerce"
        ).fillna(0).sum()

    margem_media = 0
    if "Margem_%" in base_exec.columns:
        margem_media = pd.to_numeric(
            base_exec["Margem_%"],
            errors="coerce"
        ).dropna().mean()

    produtos_curva_a = 0
    if "CURVA" in base_exec.columns:
        produtos_curva_a = (
            base_exec["CURVA"]
            .astype(str)
            .str.upper()
            .eq("A")
            .sum()
        )

    sem_custo = 0
    if "Recomendacao" in base_exec.columns:
        sem_custo = (
            base_exec["Recomendacao"]
            .astype(str)
            .str.upper()
            .str.contains("SEM CUSTO", na=False)
            .sum()
        )

    k1, k2, k3, k4 = st.columns(4)

    k1.metric(
        "Produtos Monitorados",
        f"{total_produtos:,}".replace(",", ".")
    )

    k2.metric(
        "Potencial de Captura",
        moeda_br_kpi(ganho_total)
    )

    k3.metric(
        "Rentabilidade Atual",
        percentual_br(margem_media)
    )

    k4.metric(
        "Produtos Curva A",
        f"{produtos_curva_a:,}".replace(",", ".")
    )

    k5, k6, k7, k8 = st.columns(4)

    k5.metric(
        "Produtos Sem Custo",
        f"{sem_custo:,}".replace(",", ".")
    )

    if "Laboratório" in base_exec.columns:
        k6.metric(
            "Laboratórios",
            base_exec["Laboratório"].dropna().nunique()
        )

    if "Família" in base_exec.columns:
        k7.metric(
            "Famílias",
            base_exec["Família"].dropna().nunique()
        )

    if "EAN" in base_exec.columns:
        k8.metric(
            "EANs Únicos",
            base_exec["EAN"].dropna().astype(str).nunique()
        )

    st.markdown("### 🏆 Top oportunidades financeiras")

    top = base_exec.copy()

    if "Ganho_Potencial" in top.columns:
        top["Ganho_Potencial"] = pd.to_numeric(
            top["Ganho_Potencial"],
            errors="coerce"
        ).fillna(0)

        top = top.sort_values(
            "Ganho_Potencial",
            ascending=False
        )

    cols_top = [
        c for c in [
            "EAN",
            "Produto",
            "Laboratório",
            "Família",
            "CURVA",
            "Recomendacao",
            "Preco_Medio",
            "Margem_%",
            "Ganho_Potencial",
            "Ganho_Potencial_Atualizado",
            "Ganho_Potencial_Final"
        ] if c in top.columns
    ]

    top_exibir = top[cols_top].head(20).copy()

    if "Preco_Medio" in top_exibir.columns:
        top_exibir["Preco_Medio"] = top_exibir["Preco_Medio"].apply(moeda_br)

    if "Margem_%" in top_exibir.columns:
        top_exibir["Margem_%"] = top_exibir["Margem_%"].apply(percentual_br)

    if "Ganho_Potencial" in top_exibir.columns:
        top_exibir["Ganho_Potencial"] = top_exibir["Ganho_Potencial"].apply(moeda_br)

    for _col_ganho in [
        "Ganho_Potencial",
        "Ganho_Potencial_Atualizado",
        "Ganho_Potencial_Final"
    ]:
        if _col_ganho in top_exibir.columns:
            top_exibir[_col_ganho] = top_exibir[_col_ganho].apply(moeda_br)

    st.dataframe(
        top_exibir,
        use_container_width=True,
        height=520
    )

    st.stop()




# --------------------------------------------------
# MAPA GEOGRÁFICO DE CONCORRÊNCIA
# --------------------------------------------------

if pagina == "🌎 Mapa Geográfico de Concorrência":

    st.markdown(
        """
        <div class="eirox-hero">
            <div class="eirox-section-title">Geointeligência Comercial</div>
            <h1>🌎 Mapa Geográfico de Concorrência</h1>
            <p>Visualização geográfica das farmácias, redes concorrentes, sua rede e concentração de pesquisas de preço.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    if historico.empty:
        st.warning("Não há dados de pesquisa de preços carregados em VENDA_TESTE para montar o mapa.")
        st.stop()

    mapa_base = historico.copy()
    mapa_base.columns = mapa_base.columns.astype(str).str.strip()

    col_lat = None
    col_lon = None

    for c in mapa_base.columns:
        nome = str(c).strip().lower()

        if nome in ["lat", "latitude"]:
            col_lat = c

        if nome in ["lon", "long", "longitude"]:
            col_lon = c

    if col_lat is None or col_lon is None:
        st.error("Não encontrei as colunas de latitude/longitude. A base precisa ter lat/lon ou latitude/longitude.")
        st.write("Colunas encontradas:", mapa_base.columns.tolist())
        st.stop()

    if "Farmácia" not in mapa_base.columns:
        st.error("Não encontrei a coluna Farmácia na base de pesquisas.")
        st.stop()

    if "Rede" not in mapa_base.columns:
        mapa_base["Rede"] = mapa_base["Farmácia"].apply(identificar_rede)

    if "Preço (R$)" not in mapa_base.columns:
        for col_alt in ["Preco (R$)", "Preço", "Preco", "Valor", "Valor Unitário", "Valor Unitario"]:
            if col_alt in mapa_base.columns:
                mapa_base["Preço (R$)"] = mapa_base[col_alt]
                break

    if "Preço (R$)" in mapa_base.columns:
        mapa_base["Preço (R$)"] = pd.to_numeric(mapa_base["Preço (R$)"], errors="coerce")
    else:
        mapa_base["Preço (R$)"] = None

    mapa_base[col_lat] = pd.to_numeric(mapa_base[col_lat], errors="coerce")
    mapa_base[col_lon] = pd.to_numeric(mapa_base[col_lon], errors="coerce")

    mapa_base = mapa_base.dropna(subset=[col_lat, col_lon]).copy()

    if mapa_base.empty:
        st.warning("Não existem registros com latitude e longitude válidos para montar o mapa.")
        st.stop()

    def classificar_rede_mapa(row):
        farmacia = str(row.get("Farmácia", "")).upper()
        rede = str(row.get("Rede", "")).upper()
        texto = f"{farmacia} {rede}"

        if "ZANOL" in texto or "THOMAZ" in texto:
            return "ZANOL E THOMAZ LTDA"

        if "TRIANGULO" in texto or "TRIÂNGULO" in texto:
            return "TRIANGULO DROGARIA LTDA"

        return "CONCORRENTE"

    mapa_base["Tipo_Loja"] = mapa_base.apply(classificar_rede_mapa, axis=1)

    c1, c2, c3 = st.columns([1.2, 1.2, 2])

    with c1:
        tipo_filtro = st.selectbox(
            "Tipo de loja",
            ["Todas", "ZANOL E THOMAZ LTDA", "TRIANGULO DROGARIA LTDA", "CONCORRENTE"],
            index=0,
            key="mapa_tipo_loja"
        )

    with c2:
        redes_mapa = mapa_base["Rede"].dropna().astype(str).sort_values().unique().tolist()
        rede_filtro = st.multiselect("Filtrar redes", redes_mapa, key="mapa_redes")

    with c3:
        busca_mapa = st.text_input("Buscar farmácia, rede, bairro ou cidade", key="mapa_busca")

    mapa_filtrado = mapa_base.copy()

    if tipo_filtro != "Todas":
        mapa_filtrado = mapa_filtrado[mapa_filtrado["Tipo_Loja"] == tipo_filtro]

    if rede_filtro:
        mapa_filtrado = mapa_filtrado[mapa_filtrado["Rede"].astype(str).isin(rede_filtro)]

    if busca_mapa:
        cols_busca = [
            c for c in ["Farmácia", "Rede", "Bairro", "Cidade", "Logradouro", "Produto"]
            if c in mapa_filtrado.columns
        ]

        if cols_busca:
            mask = pd.Series(False, index=mapa_filtrado.index)

            for c in cols_busca:
                mask = mask | mapa_filtrado[c].astype(str).str.contains(busca_mapa, case=False, na=False)

            mapa_filtrado = mapa_filtrado[mask].copy()

    if mapa_filtrado.empty:
        st.warning("Nenhum ponto encontrado para os filtros selecionados.")
        st.stop()

    group_cols = ["Farmácia", "Rede", "Tipo_Loja"]

    for c in ["Cidade", "Bairro", "Logradouro", "Número"]:
        if c in mapa_filtrado.columns:
            group_cols.append(c)

    mapa_agrupado = (
        mapa_filtrado
        .groupby(group_cols, dropna=False)
        .agg(
            Latitude=(col_lat, "mean"),
            Longitude=(col_lon, "mean"),
            Qtd_Pesquisas=("Farmácia", "count"),
            Preco_Medio=("Preço (R$)", "mean")
        )
        .reset_index()
    )

    mapa_agrupado["Preco_Medio"] = pd.to_numeric(mapa_agrupado["Preco_Medio"], errors="coerce")
    mapa_agrupado["Preco_Medio_Label"] = mapa_agrupado["Preco_Medio"].apply(moeda_br)

    mapa_agrupado["Texto_Mapa"] = (
        "<b>" + mapa_agrupado["Farmácia"].astype(str) + "</b>"
        + "<br>Rede: " + mapa_agrupado["Rede"].astype(str)
        + "<br>Tipo: " + mapa_agrupado["Tipo_Loja"].astype(str)
        + "<br>Pesquisas: " + mapa_agrupado["Qtd_Pesquisas"].astype(str)
        + "<br>Preço médio: " + mapa_agrupado["Preco_Medio_Label"].astype(str)
    )

    if "Cidade" in mapa_agrupado.columns:
        mapa_agrupado["Texto_Mapa"] += "<br>Cidade: " + mapa_agrupado["Cidade"].astype(str)

    if "Bairro" in mapa_agrupado.columns:
        mapa_agrupado["Texto_Mapa"] += "<br>Bairro: " + mapa_agrupado["Bairro"].astype(str)

    k1, k2, k3, k4 = st.columns(4)

    k1.metric("Farmácias no mapa", f"{mapa_agrupado['Farmácia'].nunique():,}".replace(",", "."))
    k2.metric("Redes monitoradas", f"{mapa_agrupado['Rede'].nunique():,}".replace(",", "."))
    k3.metric("Pesquisas de preço", f"{int(mapa_agrupado['Qtd_Pesquisas'].sum()):,}".replace(",", "."))
    k4.metric("Preço médio", moeda_br(mapa_agrupado["Preco_Medio"].mean()))

    centro_lat = mapa_agrupado["Latitude"].mean()
    centro_lon = mapa_agrupado["Longitude"].mean()

    mapa_agrupado["Cor"] = mapa_agrupado["Tipo_Loja"].map(
        {
            "ZANOL E THOMAZ LTDA": "#FFD500",
            "TRIANGULO DROGARIA LTDA": "#1E90FF",
            "CONCORRENTE": "#FF3B30"
        }
    ).fillna("#FF3B30")

    mapa_agrupado["Tamanho"] = mapa_agrupado["Qtd_Pesquisas"].clip(lower=1).apply(
        lambda x: min(10 + x ** 0.5 * 4, 34)
    )

    fig_mapa = go.Figure()

    for tipo, base_tipo in mapa_agrupado.groupby("Tipo_Loja"):
        fig_mapa.add_trace(
            go.Scattermapbox(
                lat=base_tipo["Latitude"],
                lon=base_tipo["Longitude"],
                mode="markers",
                marker=go.scattermapbox.Marker(
                    size=base_tipo["Tamanho"],
                    color=base_tipo["Cor"],
                    opacity=0.88
                ),
                text=base_tipo["Texto_Mapa"],
                hoverinfo="text",
                name=tipo
            )
        )

    fig_mapa.update_layout(
    legend=dict(
        orientation="h",
        yanchor="top",
        y=1.02,
        xanchor="left",
        x=0.0,
        bgcolor="rgba(0,0,0,0)"
    ),
        mapbox=dict(
            style="carto-darkmatter",
            center=dict(lat=centro_lat, lon=centro_lon),
            zoom=11
        ),
        height=680,
        margin=dict(l=0, r=0, t=20, b=0),
paper_bgcolor="rgba(0,0,0,0)"
    )

    st.plotly_chart(fig_mapa, use_container_width=True, key="mapa_geografico_concorrencia")

    st.markdown("### 🏆 Ranking de lojas por quantidade de pesquisas")

    ranking_mapa = mapa_agrupado.sort_values("Qtd_Pesquisas", ascending=False).copy()

    ranking_exibir = ranking_mapa[
        [
            c for c in ["Farmácia", "Rede", "Tipo_Loja", "Cidade", "Bairro", "Qtd_Pesquisas", "Preco_Medio_Label"]
            if c in ranking_mapa.columns
        ]
    ].rename(
        columns={
            "Tipo_Loja": "Classificação",
            "Qtd_Pesquisas": "Qtd Pesquisas",
            "Preco_Medio_Label": "Preço Médio"
        }
    )

    st.dataframe(ranking_exibir, use_container_width=True, height=420)

    csv_mapa = ranking_exibir.to_csv(index=False, sep=";").encode("utf-8-sig")

    st.download_button(
        "📥 Exportar ranking geográfico",
        csv_mapa,
        "ranking_geografico_concorrencia.csv",
        "text/csv",
        key="exportar_mapa_geografico"
    )

    st.stop()



# --------------------------------------------------
# REDE/LOJA VS CONCORRENTES
# --------------------------------------------------

if pagina == "🔎 Rede/Loja vs Concorrentes":

    st.subheader(
        "🔎 Rede/Loja vs Concorrentes"
    )

    st.info(
        "A rede ou farmácia selecionada será tratada como principal. "
        "Todas as demais lojas da base serão consideradas concorrentes para comparação."
    )

    if (
        not historico.empty
        and "Farmácia" in historico.columns
        and "Preço (R$)" in historico.columns
    ):

        analise_hist = historico.copy()

        if "Rede" not in analise_hist.columns:

            analise_hist["Rede"] = (
                analise_hist["Farmácia"]
                .apply(identificar_rede)
            )

        if "EAN" not in analise_hist.columns and "EAN (GTIN)" in analise_hist.columns:

            analise_hist["EAN"] = analise_hist["EAN (GTIN)"]

        if "EAN" in analise_hist.columns:

            analise_hist["EAN"] = (
                analise_hist["EAN"]
                .astype(str)
                .str.replace(".0", "", regex=False)
                .str.strip()
            )

        analise_hist["Preço (R$)"] = pd.to_numeric(
            analise_hist["Preço (R$)"],
            errors="coerce"
        )

        tipo_analise = st.radio(
            "Analisar por",
            [
                "Rede",
                "Farmácia"
            ],
            horizontal=True,
            key="tipo_analise_rede_loja"
        )

        if tipo_analise == "Rede":

            opcoes_analise = (
                analise_hist["Rede"]
                .dropna()
                .astype(str)
                .sort_values()
                .unique()
                .tolist()
            )

        else:

            opcoes_analise = (
                analise_hist["Farmácia"]
                .dropna()
                .astype(str)
                .sort_values()
                .unique()
                .tolist()
            )

        indice_padrao_analise = 0

        for i, opcao in enumerate(opcoes_analise):

            if "ZANOL" in str(opcao).upper():
                indice_padrao_analise = i
                break

        selecionado_analise = st.selectbox(
            f"Selecione a {tipo_analise.lower()}",
            opcoes_analise,
            index=indice_padrao_analise,
            key="select_rede_loja_analise"
        )

        if tipo_analise == "Rede":

            base_selecionada = analise_hist[
                analise_hist["Rede"] == selecionado_analise
            ].copy()

        else:

            base_selecionada = analise_hist[
                analise_hist["Farmácia"] == selecionado_analise
            ].copy()

        if not base_selecionada.empty:

            preco_selecionado = (
                base_selecionada
                .dropna(
                    subset=[
                        "EAN",
                        "Preço (R$)"
                    ]
                )
                .groupby("EAN")
                .agg(
                    Produto_Pesquisa=("Produto", "first"),
                    Preco_Selecionado=("Preço (R$)", "mean"),
                    Qtd_Pesquisas_Selecionado=("Preço (R$)", "count"),
                    Farmacia_Selecionada=("Farmácia", "first"),
                    Rede_Selecionada=("Rede", "first")
                )
                .reset_index()
            )

            hist_validos = analise_hist.dropna(
                subset=[
                    "EAN",
                    "Preço (R$)"
                ]
            ).copy()

            # --------------------------------------------------
            # DEFINIR PRINCIPAL E CONCORRENTES
            # --------------------------------------------------

            if tipo_analise == "Rede":

                hist_concorrentes = hist_validos[
                    hist_validos["Rede"] != selecionado_analise
                ].copy()

            else:

                hist_concorrentes = hist_validos[
                    hist_validos["Farmácia"] != selecionado_analise
                ].copy()

            # Todos os demais são concorrentes
            hist_concorrentes["Tipo_Comparacao"] = "Concorrente"

            # Menor preço apenas entre concorrentes
            idx_menor = (
                hist_concorrentes
                .groupby("EAN")
                ["Preço (R$)"]
                .idxmin()
            )

            menor_mercado = (
                hist_concorrentes
                .loc[
                    idx_menor,
                    [
                        "EAN",
                        "Preço (R$)",
                        "Farmácia",
                        "Rede"
                    ]
                ]
                .rename(
                    columns={
                        "Preço (R$)": "Menor_Preco_Concorrente",
                        "Farmácia": "Loja_Menor_Preco_Concorrente_Concorrente",
                        "Rede": "Rede_Menor_Preco_Concorrente_Concorrente"
                    }
                )
            )

            qtd_mercado = (
                hist_concorrentes
                .groupby("EAN")
                ["Preço (R$)"]
                .count()
                .reset_index()
                .rename(
                    columns={
                        "Preço (R$)": "Qtd_Pesquisas_Concorrentes"
                    }
                )
            )

            analise_produtos = (
                preco_selecionado
                .merge(
                    menor_mercado,
                    on="EAN",
                    how="left"
                )
                .merge(
                    qtd_mercado,
                    on="EAN",
                    how="left"
                )
            )

            if "EAN" in df_filtrado.columns:

                df_cadastro = df_filtrado.copy()

                df_cadastro["EAN"] = (
                    df_cadastro["EAN"]
                    .astype(str)
                    .str.replace(".0", "", regex=False)
                    .str.strip()
                )

                cadastro_cols = []

                for coluna in [
                    "EAN",
                    "Produto",
                    "Laboratório",
                    "Família",
                    "CURVA",
                    "Recomendacao",
                    "Ganho_Potencial",
                    "Ganho_Potencial_Atualizado",
                    "Ganho_Potencial_Final",
                    "Margem_%",
                    "Lucro_Unitario",
                    "Preco_Medio"
                ]:

                    if coluna in df_cadastro.columns:
                        cadastro_cols.append(coluna)

                df_cadastro = (
                    df_cadastro[cadastro_cols]
                    .drop_duplicates(
                        subset=[
                            "EAN"
                        ]
                    )
                )

                analise_produtos = analise_produtos.merge(
                    df_cadastro,
                    on="EAN",
                    how="left"
                )

            if (
                "simulacao_global" in globals()
                and not simulacao_global.empty
            ):

                sim = simulacao_global.copy()

                sim["EAN"] = (
                    sim["EAN"]
                    .astype(str)
                    .str.replace(".0", "", regex=False)
                    .str.strip()
                )

                sim_cols = []

                for coluna in [
                    "EAN",
                    "Qtd_Vendida_Mes_Anterior",
                    "Venda_Preco_Antigo",
                    "Preco_Atual",
                    "Preco_Sugerido_Mercado",
                    "Venda_Projetada_Preco_Sugerido",
                    "Ganho_Unitario",
                    "Ganho_Potencial_Simulador"
                ]:

                    if coluna in sim.columns:
                        sim_cols.append(coluna)

                analise_produtos = analise_produtos.merge(
                    sim[sim_cols],
                    on="EAN",
                    how="left"
                )

            analise_produtos["Dif_vs_Concorrente_R$"] = (
                analise_produtos["Preco_Selecionado"]
                - analise_produtos["Menor_Preco_Concorrente"]
            )

            analise_produtos["Dif_vs_Concorrente_%"] = (
                analise_produtos["Dif_vs_Concorrente_R$"]
                / analise_produtos["Menor_Preco_Concorrente"]
                * 100
            )

            analise_produtos["Status_vs_Concorrente"] = analise_produtos[
                "Dif_vs_Concorrente_R$"
            ].apply(
                lambda x:
                "MENOR QUE CONCORRENTE"
                if pd.notna(x) and abs(x) < 0.01
                else "ACIMA DO CONCORRENTE"
                if pd.notna(x) and x > 0
                else "ABAIXO DO CONCORRENTE"
                if pd.notna(x) and x < 0
                else ""
            )

            if "Ganho_Potencial_Simulador" in analise_produtos.columns:

                analise_produtos = analise_produtos.sort_values(
                    "Ganho_Potencial_Simulador",
                    ascending=False
                )

            k1, k2, k3, k4 = st.columns(4)

            k1.metric(
                "Produtos comuns",
                len(analise_produtos)
            )

            k2.metric(
                "Pesquisas da seleção",
                int(
                    analise_produtos[
                        "Qtd_Pesquisas_Selecionado"
                    ].sum()
                )
            )

            if "Ganho_Potencial_Simulador" in analise_produtos.columns:

                k3.metric(
                    "Ganho potencial",
                    moeda_br(
                        analise_produtos[
                            "Ganho_Potencial_Simulador"
                        ].sum()
                    )
                )

            k4.metric(
                "Diferença média vs concorrente",
                moeda_br(
                    analise_produtos[
                        "Dif_vs_Concorrente_R$"
                    ].mean()
                )
            )

            colunas_exibir = []

            for coluna in [
                "EAN",
                "Produto",
                "Produto_Pesquisa",
                "Laboratório",
                "Família",
                "CURVA",
                "Recomendacao",
                "Qtd_Pesquisas_Selecionado",
                "Qtd_Pesquisas_Concorrentes",
                "Rede_Selecionada",
                "Farmacia_Selecionada",
                "Preco_Selecionado",
                "Menor_Preco_Concorrente",
                "Loja_Menor_Preco_Concorrente",
                "Rede_Menor_Preco_Concorrente",
                "Dif_vs_Concorrente_R$",
                "Dif_vs_Concorrente_%",
                "Status_vs_Concorrente",
                "Qtd_Vendida_Mes_Anterior",
                "Venda_Preco_Antigo",
                "Preco_Atual",
                "Preco_Sugerido_Mercado",
                "Venda_Projetada_Preco_Sugerido",
                "Ganho_Unitario",
                "Ganho_Potencial_Simulador",
                "Ganho_Potencial",
                "Margem_%",
                "Lucro_Unitario",
                "Preco_Medio"
            ]:

                if coluna in analise_produtos.columns:
                    colunas_exibir.append(coluna)

            analise_exibir = analise_produtos[colunas_exibir].copy()

            for coluna in [
                "Preco_Selecionado",
                "Menor_Preco_Concorrente",
                "Dif_vs_Concorrente_R$",
                "Venda_Preco_Antigo",
                "Preco_Atual",
                "Preco_Sugerido_Mercado",
                "Venda_Projetada_Preco_Sugerido",
                "Ganho_Unitario",
                "Ganho_Potencial_Simulador",
                "Ganho_Potencial",
                "Lucro_Unitario",
                "Preco_Medio"
            ]:

                if coluna in analise_exibir.columns:
                    analise_exibir[coluna] = analise_exibir[coluna].apply(moeda_br)

            for coluna in [
                "Dif_vs_Concorrente_%",
                "Margem_%"
            ]:

                if coluna in analise_exibir.columns:
                    analise_exibir[coluna] = analise_exibir[coluna].apply(percentual_br)

            for coluna in [
                "Qtd_Vendida_Mes_Anterior"
            ]:

                if coluna in analise_exibir.columns:
                    analise_exibir[coluna] = analise_exibir[coluna].apply(numero_br)

            analise_exibir = (
                analise_exibir
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

            analise_exibir = analise_exibir.rename(
                columns={
                    "Produto_Pesquisa": "Produto na Pesquisa",
                    "Rede_Selecionada": "Rede Principal",
                    "Farmacia_Selecionada": "Farmácia Principal",
                    "Recomendacao": "Recomendação",
                    "Qtd_Pesquisas_Selecionado": "Qtd Pesquisas Seleção",
                    "Qtd_Pesquisas_Concorrentes": "Qtd Pesquisas Concorrentes",
                    "Preco_Selecionado": "Preço Principal",
                    "Menor_Preco_Concorrente": "Menor Preço Concorrente",
                    "Loja_Menor_Preco_Concorrente": "Loja Menor Preço Concorrente",
                    "Rede_Menor_Preco_Concorrente": "Rede Menor Preço Concorrente",
                    "Dif_vs_Concorrente_R$": "Dif. vs Concorrente R$",
                    "Dif_vs_Concorrente_%": "Dif. vs Concorrente %",
                    "Status_vs_Concorrente": "Status vs Concorrente",
                    "Qtd_Vendida_Mes_Anterior": "Qtd Vendida Mês Anterior",
                    "Venda_Preco_Antigo": "Venda Preço Antigo",
                    "Preco_Atual": "Preço Atual",
                    "Preco_Sugerido_Mercado": "Preço Sugerido Mercado",
                    "Venda_Projetada_Preco_Sugerido": "Venda Projetada Preço Sugerido",
                    "Ganho_Unitario": "Ganho Unitário",
                    "Ganho_Potencial_Simulador": "Ganho Produto",
                    "Ganho_Potencial": "Potencial de Captura",
                    "Margem_%": "Margem %",
                    "Lucro_Unitario": "Lucro Unitário",
                    "Preco_Medio": "Preço Médio"
                }
            )

            st.dataframe(
                analise_exibir,
                use_container_width=True,
                height=520
            )

            csv_analise = (
                analise_exibir
                .to_csv(
                    index=False,
                    sep=";"
                )
                .encode("utf-8-sig")
            )

            st.download_button(
                "📥 Exportar análise por Rede/Loja",
                csv_analise,
                f"analise_{tipo_analise.lower()}_{selecionado_analise}.csv",
                "text/csv",
                key="exportar_analise_rede_loja"
            )

        else:

            st.info(
                "Não foram encontrados produtos para a rede ou loja selecionada."
            )

    else:

        st.warning(
            "A base VENDA_TESTE não possui as colunas necessárias para essa análise."
        )

    st.stop()



# --------------------------------------------------
# NEGOCIAÇÃO COMERCIAL / COMPRAS
# --------------------------------------------------

if pagina == "🛒 Negociação Compras":

    st.subheader(
        "🛒 Negociação Compras"
    )

    st.info(
        "A rede ou farmácia selecionada será tratada como principal. "
        "Todos os demais registros serão considerados concorrentes. "
        "Esta visão mostra apenas os produtos em que o preço principal está acima do menor preço concorrente "
        "e não conseguimos acompanhar a concorrência por falta de custo, margem ou lucro suficiente. "
        "O objetivo é gerar uma lista para o comercial de compras negociar melhor condição."
    )

    if (
        not historico.empty
        and "Farmácia" in historico.columns
        and "Preço (R$)" in historico.columns
    ):

        analise_hist = historico.copy()

        if "Rede" not in analise_hist.columns:

            analise_hist["Rede"] = (
                analise_hist["Farmácia"]
                .apply(identificar_rede)
            )

        if "EAN" not in analise_hist.columns and "EAN (GTIN)" in analise_hist.columns:

            analise_hist["EAN"] = analise_hist["EAN (GTIN)"]

        if "EAN" in analise_hist.columns:

            analise_hist["EAN"] = (
                analise_hist["EAN"]
                .astype(str)
                .str.replace(".0", "", regex=False)
                .str.strip()
            )

        analise_hist["Preço (R$)"] = pd.to_numeric(
            analise_hist["Preço (R$)"],
            errors="coerce"
        )

        tipo_compra = st.radio(
            "Analisar por",
            [
                "Rede",
                "Farmácia"
            ],
            horizontal=True,
            key="tipo_negociacao_compras"
        )

        if tipo_compra == "Rede":

            opcoes_compra = (
                analise_hist["Rede"]
                .dropna()
                .astype(str)
                .sort_values()
                .unique()
                .tolist()
            )

        else:

            opcoes_compra = (
                analise_hist["Farmácia"]
                .dropna()
                .astype(str)
                .sort_values()
                .unique()
                .tolist()
            )

        indice_padrao_compra = 0

        for i, opcao in enumerate(opcoes_compra):

            if "ZANOL" in str(opcao).upper():
                indice_padrao_compra = i
                break

        selecionado_compra = st.selectbox(
            f"Selecione a {tipo_compra.lower()} principal",
            opcoes_compra,
            index=indice_padrao_compra,
            key="select_negociacao_compras"
        )

        if tipo_compra == "Rede":

            base_principal = analise_hist[
                analise_hist["Rede"] == selecionado_compra
            ].copy()

            base_concorrentes = analise_hist[
                analise_hist["Rede"] != selecionado_compra
            ].copy()

        else:

            base_principal = analise_hist[
                analise_hist["Farmácia"] == selecionado_compra
            ].copy()

            base_concorrentes = analise_hist[
                analise_hist["Farmácia"] != selecionado_compra
            ].copy()

        if (
            not base_principal.empty
            and not base_concorrentes.empty
            and "EAN" in base_principal.columns
            and "EAN" in base_concorrentes.columns
        ):

            # --------------------------------------------------
            # PREÇO PRINCIPAL
            # --------------------------------------------------

            preco_principal = (
                base_principal
                .dropna(
                    subset=[
                        "EAN",
                        "Preço (R$)"
                    ]
                )
                .groupby("EAN")
                .agg(
                    Produto_Pesquisa=("Produto", "first"),
                    Preco_Principal=("Preço (R$)", "mean"),
                    Qtd_Pesquisas_Principal=("Preço (R$)", "count"),
                    Farmacia_Principal=("Farmácia", "first"),
                    Rede_Principal=("Rede", "first")
                )
                .reset_index()
            )

            # --------------------------------------------------
            # MENOR PREÇO CONCORRENTE
            # --------------------------------------------------

            concorrentes_validos = (
                base_concorrentes
                .dropna(
                    subset=[
                        "EAN",
                        "Preço (R$)"
                    ]
                )
                .copy()
            )

            idx_menor_concorrente = (
                concorrentes_validos
                .groupby("EAN")
                ["Preço (R$)"]
                .idxmin()
            )

            menor_concorrente = (
                concorrentes_validos
                .loc[
                    idx_menor_concorrente,
                    [
                        "EAN",
                        "Preço (R$)",
                        "Farmácia",
                        "Rede"
                    ]
                ]
                .rename(
                    columns={
                        "Preço (R$)": "Menor_Preco_Concorrente",
                        "Farmácia": "Loja_Menor_Preco_Concorrente",
                        "Rede": "Rede_Menor_Preco_Concorrente"
                    }
                )
            )

            qtd_concorrentes = (
                concorrentes_validos
                .groupby("EAN")
                ["Preço (R$)"]
                .count()
                .reset_index()
                .rename(
                    columns={
                        "Preço (R$)": "Qtd_Pesquisas_Concorrentes"
                    }
                )
            )

            compras = (
                preco_principal
                .merge(
                    menor_concorrente,
                    on="EAN",
                    how="inner"
                )
                .merge(
                    qtd_concorrentes,
                    on="EAN",
                    how="left"
                )
            )

            # --------------------------------------------------
            # CADASTRO / RECOMENDAÇÃO
            # --------------------------------------------------

            if "EAN" in df_filtrado.columns:

                cadastro = df_filtrado.copy()

                cadastro["EAN"] = (
                    cadastro["EAN"]
                    .astype(str)
                    .str.replace(".0", "", regex=False)
                    .str.strip()
                )

                cadastro_cols = []

                for coluna in [
                    "EAN",
                    "Produto",
                    "Laboratório",
                    "Família",
                    "CURVA",
                    "Recomendacao",
                    "Ganho_Potencial",
                    "Ganho_Potencial_Atualizado",
                    "Ganho_Potencial_Final",
                    "Margem_%",
                    "Lucro_Unitario",
                    "Preco_Medio"
                ]:

                    if coluna in cadastro.columns:
                        cadastro_cols.append(coluna)

                cadastro = (
                    cadastro[cadastro_cols]
                    .drop_duplicates(
                        subset=[
                            "EAN"
                        ]
                    )
                )

                compras = compras.merge(
                    cadastro,
                    on="EAN",
                    how="left"
                )

            # --------------------------------------------------
            # SIMULADOR
            # --------------------------------------------------

            if (
                "simulacao_global" in globals()
                and not simulacao_global.empty
            ):

                sim = simulacao_global.copy()

                sim["EAN"] = (
                    sim["EAN"]
                    .astype(str)
                    .str.replace(".0", "", regex=False)
                    .str.strip()
                )

                sim_cols = []

                for coluna in [
                    "EAN",
                    "Qtd_Vendida_Mes_Anterior",
                    "Venda_Preco_Antigo",
                    "Preco_Atual",
                    "Preco_Sugerido_Mercado",
                    "Venda_Projetada_Preco_Sugerido",
                    "Ganho_Unitario",
                    "Ganho_Potencial_Simulador"
                ]:

                    if coluna in sim.columns:
                        sim_cols.append(coluna)

                compras = compras.merge(
                    sim[sim_cols],
                    on="EAN",
                    how="left"
                )

            # --------------------------------------------------
            # REGRA DE NEGOCIAÇÃO
            # --------------------------------------------------

            for coluna in [
                "Preco_Principal",
                "Menor_Preco_Concorrente",
                "Preco_Atual",
                "Preco_Medio",
                "Lucro_Unitario",
                "Margem_%",
                "Ganho_Potencial",
                "Ganho_Potencial_Simulador"
            ]:

                if coluna in compras.columns:
                    compras[coluna] = pd.to_numeric(
                        compras[coluna],
                        errors="coerce"
                    )

            compras["Reducao_Necessaria_R$"] = (
                compras["Preco_Principal"]
                - compras["Menor_Preco_Concorrente"]
            )

            compras["Reducao_Necessaria_%"] = (
                compras["Reducao_Necessaria_R$"]
                / compras["Preco_Principal"]
                * 100
            )

            # Custo estimado: preço atual/principal menos lucro unitário.
            # Quando não houver lucro, considera sem condição de compra.
            compras["Custo_Estimado"] = None

            if "Lucro_Unitario" in compras.columns:

                compras["Custo_Estimado"] = (
                    compras["Preco_Principal"]
                    - compras["Lucro_Unitario"]
                )

            compras["Lucro_Apos_Acompanhar"] = (
                compras["Menor_Preco_Concorrente"]
                - compras["Custo_Estimado"]
            )

            compras["Margem_Apos_Acompanhar_%"] = (
                compras["Lucro_Apos_Acompanhar"]
                / compras["Menor_Preco_Concorrente"]
                * 100
            )

            precisa_baixar = (
                compras["Reducao_Necessaria_R$"]
                .fillna(0)
                > 0
            )

            sem_condicao_custo = pd.Series(
                False,
                index=compras.index
            )

            if "Recomendacao" in compras.columns:

                sem_condicao_custo = (
                    sem_condicao_custo
                    | compras["Recomendacao"]
                        .astype(str)
                        .str.upper()
                        .str.contains(
                            "SEM CUSTO",
                            na=False
                        )
                )

            sem_condicao_custo = (
                sem_condicao_custo
                | compras["Custo_Estimado"].isna()
                | compras["Lucro_Unitario"].isna()
                | (compras["Lucro_Apos_Acompanhar"] <= 0)
                | (compras["Margem_Apos_Acompanhar_%"] <= 0)
            )

            compras_negociar = compras[
                precisa_baixar
                & sem_condicao_custo
            ].copy()

            # --------------------------------------------------
            # MOTIVO / AÇÃO
            # --------------------------------------------------

            def definir_motivo(row):

                motivos = []

                if row.get("Reducao_Necessaria_R$", 0) > 0:
                    motivos.append("Precisa baixar para acompanhar o menor concorrente")

                if "SEM CUSTO" in str(row.get("Recomendacao", "")).upper():
                    motivos.append("Sem custo cadastrado")

                if pd.isna(row.get("Custo_Estimado", None)):
                    motivos.append("Custo não identificado")

                if pd.isna(row.get("Lucro_Unitario", None)):
                    motivos.append("Lucro unitário não identificado")

                if pd.notna(row.get("Lucro_Apos_Acompanhar", None)) and row.get("Lucro_Apos_Acompanhar", 0) <= 0:
                    motivos.append("Acompanhando concorrente ficaria sem lucro")

                if pd.notna(row.get("Margem_Apos_Acompanhar_%", None)) and row.get("Margem_Apos_Acompanhar_%", 0) <= 0:
                    motivos.append("Acompanhando concorrente ficaria sem margem")

                return " | ".join(motivos)

            compras_negociar["Motivo_Compras"] = compras_negociar.apply(
                definir_motivo,
                axis=1
            )

            compras_negociar["Acao_Compras"] = (
                "Negociar custo/condição comercial antes de acompanhar o menor preço concorrente."
            )

            # --------------------------------------------------
            # KPIS
            # --------------------------------------------------

            k1, k2, k3, k4 = st.columns(4)

            k1.metric(
                "Produtos para negociar",
                len(compras_negociar)
            )

            k2.metric(
                "Pesquisas principal",
                int(
                    compras_negociar[
                        "Qtd_Pesquisas_Principal"
                    ].sum()
                )
                if "Qtd_Pesquisas_Principal" in compras_negociar.columns
                else 0
            )

            k3.metric(
                "Redução média necessária",
                moeda_br(
                    compras_negociar[
                        "Reducao_Necessaria_R$"
                    ].mean()
                )
            )

            if "Qtd_Vendida_Mes_Anterior" in compras_negociar.columns:

                k4.metric(
                    "Qtd vendida envolvida",
                    numero_br(
                        compras_negociar[
                            "Qtd_Vendida_Mes_Anterior"
                        ].sum()
                    )
                )

            # --------------------------------------------------
            # FILTROS DA VISÃO
            # --------------------------------------------------

            f1, f2, f3 = st.columns(3)

            with f1:

                filtro_rec = st.multiselect(
                    "Recomendação",
                    sorted(
                        compras_negociar["Recomendacao"]
                        .dropna()
                        .astype(str)
                        .unique()
                    )
                    if "Recomendacao" in compras_negociar.columns
                    else [],
                    key="filtro_rec_compras_principal"
                )

            with f2:

                filtro_lab = st.multiselect(
                    "Laboratório",
                    sorted(
                        compras_negociar["Laboratório"]
                        .dropna()
                        .astype(str)
                        .unique()
                    )
                    if "Laboratório" in compras_negociar.columns
                    else [],
                    key="filtro_lab_compras_principal"
                )

            with f3:

                busca_compra = st.text_input(
                    "Buscar produto ou EAN",
                    key="busca_compras_principal"
                )

            if filtro_rec and "Recomendacao" in compras_negociar.columns:

                compras_negociar = compras_negociar[
                    compras_negociar["Recomendacao"]
                    .astype(str)
                    .isin(filtro_rec)
                ]

            if filtro_lab and "Laboratório" in compras_negociar.columns:

                compras_negociar = compras_negociar[
                    compras_negociar["Laboratório"]
                    .astype(str)
                    .isin(filtro_lab)
                ]

            if busca_compra:

                cond_busca = pd.Series(
                    False,
                    index=compras_negociar.index
                )

                for coluna in [
                    "EAN",
                    "Produto",
                    "Produto_Pesquisa"
                ]:

                    if coluna in compras_negociar.columns:

                        cond_busca = (
                            cond_busca
                            | compras_negociar[coluna]
                                .astype(str)
                                .str.contains(
                                    busca_compra,
                                    case=False,
                                    na=False
                                )
                        )

                compras_negociar = compras_negociar[
                    cond_busca
                ]

            # --------------------------------------------------
            # TABELA
            # --------------------------------------------------

            compras_negociar = compras_negociar.sort_values(
                [
                    "Reducao_Necessaria_R$",
                    "Qtd_Pesquisas_Principal"
                ],
                ascending=[
                    False,
                    False
                ]
            )

            colunas_exibir = []

            for coluna in [
                "EAN",
                "Produto",
                "Produto_Pesquisa",
                "Laboratório",
                "Família",
                "CURVA",
                "Recomendacao",
                "Rede_Principal",
                "Farmacia_Principal",
                "Qtd_Pesquisas_Principal",
                "Qtd_Pesquisas_Concorrentes",
                "Preco_Principal",
                "Menor_Preco_Concorrente",
                "Loja_Menor_Preco_Concorrente",
                "Rede_Menor_Preco_Concorrente",
                "Reducao_Necessaria_R$",
                "Reducao_Necessaria_%",
                "Custo_Estimado",
                "Lucro_Unitario",
                "Margem_%",
                "Lucro_Apos_Acompanhar",
                "Margem_Apos_Acompanhar_%",
                "Qtd_Vendida_Mes_Anterior",
                "Motivo_Compras",
                "Acao_Compras"
            ]:

                if coluna in compras_negociar.columns:
                    colunas_exibir.append(coluna)

            compras_exibir = compras_negociar[colunas_exibir].copy()

            for coluna in [
                "Preco_Principal",
                "Menor_Preco_Concorrente",
                "Reducao_Necessaria_R$",
                "Custo_Estimado",
                "Lucro_Unitario",
                "Lucro_Apos_Acompanhar"
            ]:

                if coluna in compras_exibir.columns:
                    compras_exibir[coluna] = compras_exibir[coluna].apply(moeda_br)

            for coluna in [
                "Reducao_Necessaria_%",
                "Margem_%",
                "Margem_Apos_Acompanhar_%"
            ]:

                if coluna in compras_exibir.columns:
                    compras_exibir[coluna] = compras_exibir[coluna].apply(percentual_br)

            if "Qtd_Vendida_Mes_Anterior" in compras_exibir.columns:

                compras_exibir["Qtd_Vendida_Mes_Anterior"] = (
                    compras_exibir["Qtd_Vendida_Mes_Anterior"]
                    .apply(numero_br)
                )

            compras_exibir = compras_exibir.rename(
                columns={
                    "Produto_Pesquisa": "Produto na Pesquisa",
                    "Recomendacao": "Recomendação",
                    "Rede_Principal": "Rede Principal",
                    "Farmacia_Principal": "Farmácia Principal",
                    "Qtd_Pesquisas_Principal": "Qtd Pesquisas Principal",
                    "Qtd_Pesquisas_Concorrentes": "Qtd Pesquisas Concorrentes",
                    "Preco_Principal": "Preço Principal",
                    "Menor_Preco_Concorrente": "Menor Preço Concorrente",
                    "Loja_Menor_Preco_Concorrente": "Loja Menor Preço Concorrente",
                    "Rede_Menor_Preco_Concorrente": "Rede Menor Preço Concorrente",
                    "Reducao_Necessaria_R$": "Redução Necessária R$",
                    "Reducao_Necessaria_%": "Redução Necessária %",
                    "Custo_Estimado": "Custo Estimado",
                    "Lucro_Unitario": "Lucro Atual",
                    "Margem_%": "Margem Atual %",
                    "Lucro_Apos_Acompanhar": "Lucro Após Acompanhar",
                    "Margem_Apos_Acompanhar_%": "Margem Após Acompanhar %",
                    "Qtd_Vendida_Mes_Anterior": "Qtd Vendida Mês Anterior",
                    "Motivo_Compras": "Motivo para Compras",
                    "Acao_Compras": "Ação Compras"
                }
            )

            compras_exibir = (
                compras_exibir
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
                compras_exibir,
                use_container_width=True,
                height=560
            )

            csv_compras = (
                compras_exibir
                .to_csv(
                    index=False,
                    sep=";"
                )
                .encode("utf-8-sig")
            )

            st.download_button(
                "📥 Exportar lista para Comercial de Compras",
                csv_compras,
                "produtos_para_negociacao_compras.csv",
                "text/csv",
                key="exportar_lista_compras_principal"
            )

        else:

            st.warning(
                "Não há dados suficientes para comparar a rede/farmácia principal contra concorrentes."
            )

    else:

        st.warning(
            "A base VENDA_TESTE não possui dados suficientes para montar esta visão."
        )

    st.stop()



# --------------------------------------------------
# CENTRAL DE ALERTAS INTELIGENTES
# --------------------------------------------------

if pagina == "🚨 Central de Alertas":

    st.subheader(
        "🚨 Central de Alertas Inteligentes"
    )

    st.info(
        "Esta central prioriza produtos que exigem ação do time de pricing, comercial ou compras. "
        "Os alertas são calculados com base em preço principal, menor concorrente, recomendação, custo/margem e potencial financeiro."
    )

    if (
        not historico.empty
        and "Farmácia" in historico.columns
        and "Preço (R$)" in historico.columns
    ):

        alertas_hist = historico.copy()

        if "Rede" not in alertas_hist.columns:

            alertas_hist["Rede"] = (
                alertas_hist["Farmácia"]
                .apply(identificar_rede)
            )

        if "EAN" not in alertas_hist.columns and "EAN (GTIN)" in alertas_hist.columns:

            alertas_hist["EAN"] = alertas_hist["EAN (GTIN)"]

        if "EAN" in alertas_hist.columns:

            alertas_hist["EAN"] = (
                alertas_hist["EAN"]
                .astype(str)
                .str.replace(".0", "", regex=False)
                .str.strip()
            )

        alertas_hist["Preço (R$)"] = pd.to_numeric(
            alertas_hist["Preço (R$)"],
            errors="coerce"
        )

        tipo_alerta_base = st.radio(
            "Analisar alertas por",
            [
                "Rede",
                "Farmácia"
            ],
            horizontal=True,
            key="tipo_central_alertas"
        )

        if tipo_alerta_base == "Rede":

            opcoes_alerta = (
                alertas_hist["Rede"]
                .dropna()
                .astype(str)
                .sort_values()
                .unique()
                .tolist()
            )

        else:

            opcoes_alerta = (
                alertas_hist["Farmácia"]
                .dropna()
                .astype(str)
                .sort_values()
                .unique()
                .tolist()
            )

        indice_padrao_alerta = 0

        for i, opcao in enumerate(opcoes_alerta):

            if "ZANOL" in str(opcao).upper():
                indice_padrao_alerta = i
                break

        selecionado_alerta = st.selectbox(
            f"Selecione a {tipo_alerta_base.lower()} principal",
            opcoes_alerta,
            index=indice_padrao_alerta,
            key="select_central_alertas"
        )

        if tipo_alerta_base == "Rede":

            base_principal_alerta = alertas_hist[
                alertas_hist["Rede"] == selecionado_alerta
            ].copy()

            base_concorrente_alerta = alertas_hist[
                alertas_hist["Rede"] != selecionado_alerta
            ].copy()

        else:

            base_principal_alerta = alertas_hist[
                alertas_hist["Farmácia"] == selecionado_alerta
            ].copy()

            base_concorrente_alerta = alertas_hist[
                alertas_hist["Farmácia"] != selecionado_alerta
            ].copy()

        if (
            not base_principal_alerta.empty
            and not base_concorrente_alerta.empty
            and "EAN" in base_principal_alerta.columns
            and "EAN" in base_concorrente_alerta.columns
        ):

            principal = (
                base_principal_alerta
                .dropna(
                    subset=[
                        "EAN",
                        "Preço (R$)"
                    ]
                )
                .groupby("EAN")
                .agg(
                    Produto_Pesquisa=("Produto", "first"),
                    Preco_Principal=("Preço (R$)", "mean"),
                    Qtd_Pesquisas_Principal=("Preço (R$)", "count"),
                    Farmacia_Principal=("Farmácia", "first"),
                    Rede_Principal=("Rede", "first")
                )
                .reset_index()
            )

            concorrentes_validos = (
                base_concorrente_alerta
                .dropna(
                    subset=[
                        "EAN",
                        "Preço (R$)"
                    ]
                )
                .copy()
            )

            idx_menor = (
                concorrentes_validos
                .groupby("EAN")
                ["Preço (R$)"]
                .idxmin()
            )

            menor_concorrente = (
                concorrentes_validos
                .loc[
                    idx_menor,
                    [
                        "EAN",
                        "Preço (R$)",
                        "Farmácia",
                        "Rede"
                    ]
                ]
                .rename(
                    columns={
                        "Preço (R$)": "Menor_Preco_Concorrente",
                        "Farmácia": "Loja_Menor_Preco_Concorrente",
                        "Rede": "Rede_Menor_Preco_Concorrente"
                    }
                )
            )

            qtd_concorrentes = (
                concorrentes_validos
                .groupby("EAN")
                ["Preço (R$)"]
                .count()
                .reset_index()
                .rename(
                    columns={
                        "Preço (R$)": "Qtd_Pesquisas_Concorrentes"
                    }
                )
            )

            alertas_base = (
                principal
                .merge(
                    menor_concorrente,
                    on="EAN",
                    how="left"
                )
                .merge(
                    qtd_concorrentes,
                    on="EAN",
                    how="left"
                )
            )

            if "EAN" in df_filtrado.columns:

                cadastro_alerta = df_filtrado.copy()

                cadastro_alerta["EAN"] = (
                    cadastro_alerta["EAN"]
                    .astype(str)
                    .str.replace(".0", "", regex=False)
                    .str.strip()
                )

                cadastro_cols = []

                for coluna in [
                    "EAN",
                    "Produto",
                    "Laboratório",
                    "Família",
                    "CURVA",
                    "Recomendacao",
                    "Ganho_Potencial",
                    "Ganho_Potencial_Atualizado",
                    "Ganho_Potencial_Final",
                    "Margem_%",
                    "Lucro_Unitario",
                    "Preco_Medio"
                ]:

                    if coluna in cadastro_alerta.columns:
                        cadastro_cols.append(coluna)

                cadastro_alerta = (
                    cadastro_alerta[cadastro_cols]
                    .drop_duplicates(
                        subset=[
                            "EAN"
                        ]
                    )
                )

                alertas_base = alertas_base.merge(
                    cadastro_alerta,
                    on="EAN",
                    how="left"
                )

            if (
                "simulacao_global" in globals()
                and not simulacao_global.empty
            ):

                sim_alerta = simulacao_global.copy()

                sim_alerta["EAN"] = (
                    sim_alerta["EAN"]
                    .astype(str)
                    .str.replace(".0", "", regex=False)
                    .str.strip()
                )

                sim_cols = []

                for coluna in [
                    "EAN",
                    "Qtd_Vendida_Mes_Anterior",
                    "Venda_Preco_Antigo",
                    "Preco_Atual",
                    "Preco_Sugerido_Mercado",
                    "Venda_Projetada_Preco_Sugerido",
                    "Ganho_Unitario",
                    "Ganho_Potencial_Simulador"
                ]:

                    if coluna in sim_alerta.columns:
                        sim_cols.append(coluna)

                alertas_base = alertas_base.merge(
                    sim_alerta[sim_cols],
                    on="EAN",
                    how="left"
                )

            for coluna in [
                "Preco_Principal",
                "Menor_Preco_Concorrente",
                "Ganho_Potencial",
                "Ganho_Potencial_Simulador",
                "Margem_%",
                "Lucro_Unitario",
                "Preco_Atual"
            ]:

                if coluna in alertas_base.columns:

                    alertas_base[coluna] = pd.to_numeric(
                        alertas_base[coluna],
                        errors="coerce"
                    )

            alertas_base["Dif_vs_Concorrente_R$"] = (
                alertas_base["Preco_Principal"]
                - alertas_base["Menor_Preco_Concorrente"]
            )

            alertas_base["Dif_vs_Concorrente_%"] = (
                alertas_base["Dif_vs_Concorrente_R$"]
                / alertas_base["Menor_Preco_Concorrente"]
                * 100
            )

            alertas_base["Custo_Estimado"] = None

            if "Lucro_Unitario" in alertas_base.columns:

                alertas_base["Custo_Estimado"] = (
                    alertas_base["Preco_Principal"]
                    - alertas_base["Lucro_Unitario"]
                )

            alertas_base["Lucro_Apos_Acompanhar"] = (
                alertas_base["Menor_Preco_Concorrente"]
                - alertas_base["Custo_Estimado"]
            )

            alertas_base["Margem_Apos_Acompanhar_%"] = (
                alertas_base["Lucro_Apos_Acompanhar"]
                / alertas_base["Menor_Preco_Concorrente"]
                * 100
            )

            def classificar_alerta(row):

                dif_perc = row.get(
                    "Dif_vs_Concorrente_%",
                    0
                )

                ganho = row.get(
                    "Ganho_Potencial_Simulador",
                    row.get(
                        "Ganho_Potencial",
                        0
                    )
                )

                recomendacao = str(
                    row.get(
                        "Recomendacao",
                        ""
                    )
                ).upper()

                lucro_apos = row.get(
                    "Lucro_Apos_Acompanhar",
                    None
                )

                margem_apos = row.get(
                    "Margem_Apos_Acompanhar_%",
                    None
                )

                if (
                    pd.notna(dif_perc)
                    and dif_perc >= 15
                    and (
                        pd.isna(lucro_apos)
                        or lucro_apos <= 0
                        or pd.isna(margem_apos)
                        or margem_apos <= 0
                    )
                ):

                    return "🔴 Negociar Compras"

                if (
                    pd.notna(dif_perc)
                    and dif_perc >= 15
                ):

                    return "🔴 Perda Competitiva"

                if "SEM CUSTO" in recomendacao:

                    return "🟠 Produto Sem Custo"

                if (
                    pd.notna(ganho)
                    and ganho > 0
                    and "SUBIR PREÇO" in recomendacao
                ):

                    return "🟢 Ganho Rápido"

                if (
                    pd.notna(dif_perc)
                    and dif_perc >= 5
                ):

                    return "🟡 Atenção Competitiva"

                return "⚪ Monitorar"

            alertas_base["Tipo_Alerta"] = alertas_base.apply(
                classificar_alerta,
                axis=1
            )

            def definir_prioridade(row):

                tipo = str(
                    row.get(
                        "Tipo_Alerta",
                        ""
                    )
                )

                dif = row.get(
                    "Dif_vs_Concorrente_%",
                    0
                )

                qtd = row.get(
                    "Qtd_Pesquisas_Principal",
                    0
                )

                curva = str(
                    row.get(
                        "CURVA",
                        ""
                    )
                ).upper()

                score = 0

                if "🔴" in tipo:
                    score += 60

                elif "🟠" in tipo:
                    score += 45

                elif "🟡" in tipo:
                    score += 30

                elif "🟢" in tipo:
                    score += 25

                if pd.notna(dif):
                    score += min(
                        abs(float(dif)),
                        30
                    )

                if pd.notna(qtd):
                    score += min(
                        float(qtd),
                        20
                    )

                if curva == "A":
                    score += 15

                if score >= 85:
                    return "🔴 Crítica"

                if score >= 60:
                    return "🟠 Alta"

                if score >= 35:
                    return "🟡 Média"

                return "🟢 Baixa"

            alertas_base["Prioridade"] = alertas_base.apply(
                definir_prioridade,
                axis=1
            )

            def acao_alerta(row):

                tipo = str(
                    row.get(
                        "Tipo_Alerta",
                        ""
                    )
                )

                if "Negociar Compras" in tipo:
                    return "Enviar para compras negociar custo/condição antes de reduzir."

                if "Perda Competitiva" in tipo:
                    return "Avaliar redução de preço ou ação promocional."

                if "Produto Sem Custo" in tipo:
                    return "Regularizar custo/cadastro antes de decisão comercial."

                if "Ganho Rápido" in tipo:
                    return "Avaliar aumento de preço com baixo risco competitivo."

                if "Atenção Competitiva" in tipo:
                    return "Monitorar e comparar histórico antes de ajustar."

                return "Manter em monitoramento."

            alertas_base["Ação Recomendada"] = alertas_base.apply(
                acao_alerta,
                axis=1
            )

            f1, f2, f3, f4 = st.columns(4)

            with f1:

                filtro_tipo_alerta = st.multiselect(
                    "Tipo de alerta",
                    sorted(
                        alertas_base["Tipo_Alerta"]
                        .dropna()
                        .unique()
                    ),
                    key="filtro_tipo_alerta"
                )

            with f2:

                filtro_prioridade = st.multiselect(
                    "Prioridade",
                    sorted(
                        alertas_base["Prioridade"]
                        .dropna()
                        .unique()
                    ),
                    key="filtro_prioridade_alerta"
                )

            with f3:

                filtro_lab_alerta = st.multiselect(
                    "Laboratório",
                    sorted(
                        alertas_base["Laboratório"]
                        .dropna()
                        .astype(str)
                        .unique()
                    )
                    if "Laboratório" in alertas_base.columns
                    else [],
                    key="filtro_lab_alerta"
                )

            with f4:

                busca_alerta = st.text_input(
                    "Buscar produto ou EAN",
                    key="busca_alerta"
                )

            alertas_filtrados = alertas_base.copy()

            if filtro_tipo_alerta:

                alertas_filtrados = alertas_filtrados[
                    alertas_filtrados["Tipo_Alerta"]
                    .isin(filtro_tipo_alerta)
                ]

            if filtro_prioridade:

                alertas_filtrados = alertas_filtrados[
                    alertas_filtrados["Prioridade"]
                    .isin(filtro_prioridade)
                ]

            if filtro_lab_alerta and "Laboratório" in alertas_filtrados.columns:

                alertas_filtrados = alertas_filtrados[
                    alertas_filtrados["Laboratório"]
                    .astype(str)
                    .isin(filtro_lab_alerta)
                ]

            if busca_alerta:

                cond_busca_alerta = pd.Series(
                    False,
                    index=alertas_filtrados.index
                )

                for coluna in [
                    "EAN",
                    "Produto",
                    "Produto_Pesquisa"
                ]:

                    if coluna in alertas_filtrados.columns:

                        cond_busca_alerta = (
                            cond_busca_alerta
                            | alertas_filtrados[coluna]
                                .astype(str)
                                .str.contains(
                                    busca_alerta,
                                    case=False,
                                    na=False
                                )
                        )

                alertas_filtrados = alertas_filtrados[
                    cond_busca_alerta
                ]

            k1, k2, k3, k4 = st.columns(4)

            k1.metric(
                "Alertas",
                len(alertas_filtrados)
            )

            k2.metric(
                "Críticos",
                int(
                    alertas_filtrados[
                        alertas_filtrados["Prioridade"]
                        .astype(str)
                        .str.contains(
                            "Crítica",
                            na=False
                        )
                    ].shape[0]
                )
            )

            k3.metric(
                "Negociar Compras",
                int(
                    alertas_filtrados[
                        alertas_filtrados["Tipo_Alerta"]
                        .astype(str)
                        .str.contains(
                            "Negociar Compras",
                            na=False
                        )
                    ].shape[0]
                )
            )

            ganho_total_alerta = 0

            if "Ganho_Potencial_Simulador" in alertas_filtrados.columns:

                ganho_total_alerta = (
                    alertas_filtrados[
                        "Ganho_Potencial_Simulador"
                    ]
                    .fillna(0)
                    .sum()
                )

            elif "Ganho_Potencial" in alertas_filtrados.columns:

                ganho_total_alerta = (
                    alertas_filtrados[
                        "Ganho_Potencial"
                    ]
                    .fillna(0)
                    .sum()
                )

            k4.metric(
                "Potencial envolvido",
                moeda_br(
                    ganho_total_alerta
                )
            )

            g1, g2 = st.columns(2)

            with g1:

                resumo_alertas = (
                    alertas_filtrados["Tipo_Alerta"]
                    .value_counts()
                    .reset_index()
                )

                resumo_alertas.columns = [
                    "Tipo de Alerta",
                    "Quantidade"
                ]

                fig_alertas = px.bar(
                    resumo_alertas,
                    x="Tipo de Alerta",
                    y="Quantidade",
                    text="Quantidade",
                    title="Alertas por Tipo"
                )

                fig_alertas.update_traces(
                    textposition="outside"
                )

                st.plotly_chart(
                    fig_alertas,
                    width="stretch",
                    key="grafico_alertas_tipo"
                )

            with g2:

                resumo_prioridade = (
                    alertas_filtrados["Prioridade"]
                    .value_counts()
                    .reset_index()
                )

                resumo_prioridade.columns = [
                    "Prioridade",
                    "Quantidade"
                ]

                fig_prioridade = px.bar(
                    resumo_prioridade,
                    x="Prioridade",
                    y="Quantidade",
                    text="Quantidade",
                    title="Alertas por Prioridade"
                )

                fig_prioridade.update_traces(
                    textposition="outside"
                )

                st.plotly_chart(
                    fig_prioridade,
                    width="stretch",
                    key="grafico_alertas_prioridade"
                )

            ordem_prioridade = {
                "🔴 Crítica": 1,
                "🟠 Alta": 2,
                "🟡 Média": 3,
                "🟢 Baixa": 4
            }

            alertas_filtrados["Ordem_Prioridade"] = (
                alertas_filtrados["Prioridade"]
                .map(ordem_prioridade)
                .fillna(9)
            )

            alertas_filtrados = alertas_filtrados.sort_values(
                [
                    "Ordem_Prioridade",
                    "Dif_vs_Concorrente_%"
                ],
                ascending=[
                    True,
                    False
                ]
            )

            colunas_alerta = []

            for coluna in [
                "Prioridade",
                "Tipo_Alerta",
                "EAN",
                "Produto",
                "Produto_Pesquisa",
                "Laboratório",
                "Família",
                "CURVA",
                "Recomendacao",
                "Rede_Principal",
                "Farmacia_Principal",
                "Qtd_Pesquisas_Principal",
                "Qtd_Pesquisas_Concorrentes",
                "Preco_Principal",
                "Menor_Preco_Concorrente",
                "Loja_Menor_Preco_Concorrente",
                "Rede_Menor_Preco_Concorrente",
                "Dif_vs_Concorrente_R$",
                "Dif_vs_Concorrente_%",
                "Lucro_Apos_Acompanhar",
                "Margem_Apos_Acompanhar_%",
                "Ganho_Potencial_Simulador",
                "Ação Recomendada"
            ]:

                if coluna in alertas_filtrados.columns:
                    colunas_alerta.append(coluna)

            alertas_exibir = alertas_filtrados[colunas_alerta].copy()

            for coluna in [
                "Preco_Principal",
                "Menor_Preco_Concorrente",
                "Dif_vs_Concorrente_R$",
                "Lucro_Apos_Acompanhar",
                "Ganho_Potencial_Simulador"
            ]:

                if coluna in alertas_exibir.columns:
                    alertas_exibir[coluna] = alertas_exibir[coluna].apply(moeda_br)

            for coluna in [
                "Dif_vs_Concorrente_%",
                "Margem_Apos_Acompanhar_%"
            ]:

                if coluna in alertas_exibir.columns:
                    alertas_exibir[coluna] = alertas_exibir[coluna].apply(percentual_br)

            alertas_exibir = alertas_exibir.rename(
                columns={
                    "Tipo_Alerta": "Tipo de Alerta",
                    "Produto_Pesquisa": "Produto na Pesquisa",
                    "Recomendacao": "Recomendação",
                    "Rede_Principal": "Rede Principal",
                    "Farmacia_Principal": "Farmácia Principal",
                    "Qtd_Pesquisas_Principal": "Qtd Pesquisas Principal",
                    "Qtd_Pesquisas_Concorrentes": "Qtd Pesquisas Concorrentes",
                    "Preco_Principal": "Preço Principal",
                    "Menor_Preco_Concorrente": "Menor Preço Concorrente",
                    "Loja_Menor_Preco_Concorrente": "Loja Menor Preço Concorrente",
                    "Rede_Menor_Preco_Concorrente": "Rede Menor Preço Concorrente",
                    "Dif_vs_Concorrente_R$": "Dif. vs Concorrente R$",
                    "Dif_vs_Concorrente_%": "Dif. vs Concorrente %",
                    "Lucro_Apos_Acompanhar": "Lucro Após Acompanhar",
                    "Margem_Apos_Acompanhar_%": "Margem Após Acompanhar %",
                    "Ganho_Potencial_Simulador": "Potencial"
                }
            )

            alertas_exibir = (
                alertas_exibir
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
                alertas_exibir,
                use_container_width=True,
                height=560
            )

            csv_alertas = (
                alertas_exibir
                .to_csv(
                    index=False,
                    sep=";"
                )
                .encode("utf-8-sig")
            )

            st.download_button(
                "📥 Exportar Central de Alertas",
                csv_alertas,
                "central_alertas_eirox.csv",
                "text/csv",
                key="exportar_central_alertas"
            )

        else:

            st.warning(
                "Não há dados suficientes para comparar principal contra concorrentes."
            )

    else:

        st.warning(
            "A base de pesquisa de preços não possui dados suficientes para montar os alertas."
        )

    st.stop()



# Aviso técnico quando o simulador estiver usando fallback do histórico
if origem_simulacao_global == "historico_pesquisa":
    st.info(
        "ℹ️ O simulador operacional está usando o histórico de pesquisa como apoio, "
        "mas o Ganho Potencial exibido no dashboard permanece o valor oficial da Analise_Pricing.xlsx."
    )


if "origem_simulacao_global" in globals():
    if origem_simulacao_global == "venda_rede_historico_inteligente":
        pass

    else:
        st.info("ℹ️ Motor inteligente sem base completa. Usando Ganho_Potencial oficial da Analise_Pricing.xlsx.")

if "Ganho_Potencial" in df_filtrado.columns:
    ganho_total_atualizado = pd.to_numeric(
        df_filtrado["Ganho_Potencial"],
        errors="coerce"
    ).fillna(0).sum()
else:
    ganho_total_atualizado = 0

# --------------------------------------------------
# KPIS
# --------------------------------------------------

# Card Potencial de Captura ampliado para evitar corte do valor.
k1,k2,k3,k4,k5,k6 = st.columns([1, 1, 1, 1.65, 1, 1])

k1.metric(
    "Produtos",
    len(df_filtrado)
)

k2.metric(
    "Rentabilidade Atual",
    percentual_br(df_filtrado["Margem_%"].mean())
)

k3.metric(
    "Lucro Médio",
    moeda_br(df_filtrado["Lucro_Unitario"].mean())
)

k4.metric(
    "Potencial de Captura",
    moeda_br_kpi(df_filtrado["Ganho_Potencial"].sum())
)

k5.metric(
    "Laboratórios",
    df_filtrado["Laboratório"].nunique()
)

k6.metric(
    "Preço Médio",
    moeda_br(df_filtrado["Preco_Medio"].mean())
)

explicacao_calculo(
    "Indicadores principais do Painel Geral",
    [
        "Produtos = quantidade de linhas/produtos após os filtros aplicados.",
        "Margem Média = média da coluna Margem_% dos produtos filtrados.",
        "Lucro Médio = média da coluna Lucro_Unitario dos produtos filtrados.",
        "Ganho Potencial = soma da coluna Ganho_Potencial dos produtos filtrados.",
        "Laboratórios = quantidade de laboratórios únicos após os filtros.",
        "Preço Médio = média da coluna Preco_Medio dos produtos filtrados."
    ]
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

# Ações recomendadas
st.subheader(
    "📋 Ações Recomendadas"
)

explicacao_calculo(
    "Ações recomendadas",
    [
        "A tabela conta quantos produtos existem em cada Recomendacao dentro do filtro atual.",
        "Cada recomendação recebe uma orientação comercial padrão: subir preço, manter, analisar redução ou corrigir cadastro.",
        "Ao selecionar uma recomendação, o painel detalha somente os produtos pertencentes àquela ação."
    ]
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

    lista_recomendacoes = acoes_df["Recomendacao"].tolist()

    indice_recomendacao_padrao = 0

    if "SUBIR PREÇO" in lista_recomendacoes:
        indice_recomendacao_padrao = lista_recomendacoes.index("SUBIR PREÇO")

    recomendacao_selecionada = st.selectbox(
        "Selecione a recomendação para detalhar",
        lista_recomendacoes,
        index=indice_recomendacao_padrao,
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

    # --------------------------------------------------
    # CUSTO UNITÁRIO PELA VENDA_FINAL_TESTE
    # --------------------------------------------------
    # Regra solicitada:
    # Custo unitário = soma da coluna "Custo" / soma da coluna "Itens"
    # A origem é a base venda_rede, carregada da pasta VENDA_FINAL_TESTE.

    try:

        if "Custo" not in produtos_detalhe.columns and isinstance(venda_rede, pd.DataFrame) and not venda_rede.empty:

            base_custo_venda = venda_rede.copy()
            base_custo_venda.columns = base_custo_venda.columns.astype(str).str.strip()

            col_ean_custo = achar_coluna(
                base_custo_venda,
                [
                    "EAN",
                    "EAN (GTIN)",
                    "GTIN",
                    "Código de Barras",
                    "Codigo de Barras",
                    "Cód. Barras/Etiq.",
                    "Cod. Barras/Etiq."
                ],
                [
                    "ean",
                    "gtin",
                    "barras"
                ]
            )

            col_custo_venda = achar_coluna(
                base_custo_venda,
                [
                    "Custo",
                    "CUSTO",
                    "Valor Custo",
                    "Custo Total",
                    "CMV"
                ],
                [
                    "custo",
                    "cmv"
                ]
            )

            col_itens_venda = achar_coluna(
                base_custo_venda,
                [
                    "Itens",
                    "Item",
                    "Quantidade",
                    "Qtd",
                    "QTD",
                    "Qtde",
                    "Unidades"
                ],
                [
                    "itens",
                    "item",
                    "qtd",
                    "quant",
                    "qtde",
                    "unid"
                ]
            )

            if col_ean_custo and col_custo_venda and col_itens_venda:

                base_custo_venda["EAN"] = (
                    base_custo_venda[col_ean_custo]
                    .astype(str)
                    .str.replace(".0", "", regex=False)
                    .str.strip()
                )

                base_custo_venda["Custo_Total_Venda_Final"] = converter_numero_brasil(
                    base_custo_venda[col_custo_venda]
                )

                base_custo_venda["Itens_Venda_Final"] = converter_numero_brasil(
                    base_custo_venda[col_itens_venda]
                )

                custo_por_ean = (
                    base_custo_venda
                    .dropna(subset=["EAN", "Custo_Total_Venda_Final", "Itens_Venda_Final"])
                    .groupby("EAN", as_index=False)
                    .agg(
                        Custo_Total_Venda_Final=("Custo_Total_Venda_Final", "sum"),
                        Itens_Venda_Final=("Itens_Venda_Final", "sum")
                    )
                )

                custo_por_ean = custo_por_ean[
                    custo_por_ean["Itens_Venda_Final"] > 0
                ].copy()

                custo_por_ean["Custo"] = (
                    custo_por_ean["Custo_Total_Venda_Final"]
                    / custo_por_ean["Itens_Venda_Final"]
                )

                produtos_detalhe = produtos_detalhe.merge(
                    custo_por_ean[["EAN", "Custo"]],
                    on="EAN",
                    how="left"
                )

    except Exception:
        pass

    # --------------------------------------------------
    # MENOR PREÇO E LOJA COM MENOR PREÇO
    # --------------------------------------------------

    if (
        not historico.empty
        and "Preço (R$)" in historico.columns
        and "Farmácia" in historico.columns
    ):

        hist_menor = historico.copy()

        if "EAN" not in hist_menor.columns and "EAN (GTIN)" in hist_menor.columns:
            hist_menor["EAN"] = hist_menor["EAN (GTIN)"]

        if "EAN" in hist_menor.columns:

            hist_menor["EAN"] = (
                hist_menor["EAN"]
                .astype(str)
                .str.replace(".0", "", regex=False)
                .str.strip()
            )

            hist_menor["Preço (R$)"] = pd.to_numeric(
                hist_menor["Preço (R$)"],
                errors="coerce"
            )

            hist_menor = hist_menor.dropna(
                subset=[
                    "EAN",
                    "Preço (R$)"
                ]
            )

            idx_menor_preco = (
                hist_menor
                .groupby("EAN")
                ["Preço (R$)"]
                .idxmin()
            )

            menor_preco_loja = (
                hist_menor
                .loc[
                    idx_menor_preco,
                    [
                        "EAN",
                        "Preço (R$)",
                        "Farmácia"
                    ]
                ]
                .rename(
                    columns={
                        "Preço (R$)": "Menor_Preco",
                        "Farmácia": "Loja_Menor_Preco_Concorrente"
                    }
                )
            )

            produtos_detalhe = produtos_detalhe.merge(
                menor_preco_loja,
                on="EAN",
                how="left"
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
        "Produto",
        "Laboratório",
        "Família",
        "CURVA",
        "Recomendacao",
        "Qtd_Vendida_Mes_Anterior",
        "Venda_Preco_Antigo",
        "Venda_Projetada_Preco_Sugerido",
        "Custo",
        "Preco_Atual",
        "Preco_Sugerido_Mercado",
        "Ganho_Unitario",
        "Ganho_Potencial_Simulador",
        "Menor_Preco",
        "Loja_Menor_Preco_Concorrente",
        "Margem_%",
        "Lucro_Unitario",
        "Preco_Medio"
    ]:

        if coluna in produtos_detalhe.columns:
            colunas_exibir.append(coluna)

    produtos_exibir = produtos_detalhe[colunas_exibir].copy()

    # Nova coluna: Margem considerando seguir o menor preço do mercado.
    # IMPORTANTE: mantém a coluna original Margem_% sem alteração.
    # Fórmula: (Menor Preço - Custo) / Menor Preço * 100
    if "Custo" in produtos_exibir.columns and "Menor_Preco" in produtos_exibir.columns:
        custo_num = pd.to_numeric(produtos_exibir["Custo"], errors="coerce")
        menor_preco_num = pd.to_numeric(produtos_exibir["Menor_Preco"], errors="coerce")
        produtos_exibir["Margem_%_Menor_Preco"] = np.where(
            menor_preco_num > 0,
            ((menor_preco_num - custo_num) / menor_preco_num) * 100,
            np.nan
        )

    # --------------------------------------------------
    # FORMATAR PADRÃO BRASIL
    # --------------------------------------------------

    for coluna in [
        "Venda_Preco_Antigo",
        "Venda_Projetada_Preco_Sugerido",
        "Custo",
        "Preco_Atual",
        "Preco_Sugerido_Mercado",
        "Ganho_Unitario",
        "Ganho_Potencial_Simulador",
        "Menor_Preco",
        "Lucro_Unitario",
        "Preco_Medio"
    ]:

        if coluna in produtos_exibir.columns:
            produtos_exibir[coluna] = produtos_exibir[coluna].apply(moeda_br)

    if "Margem_%" in produtos_exibir.columns:
        produtos_exibir["Margem_%"] = produtos_exibir["Margem_%"].apply(percentual_br)

    if "Margem_%_Menor_Preco" in produtos_exibir.columns:
        produtos_exibir["Margem_%_Menor_Preco"] = produtos_exibir["Margem_%_Menor_Preco"].apply(percentual_br)

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

    produtos_exibir = produtos_exibir.rename(
        columns={
            "Preco_Atual": "Preço Atual",
            "Preco_Sugerido_Mercado": "Preço Sugerido Mercado",
            "Venda_Preco_Antigo": "Venda Preço Antigo",
            "Venda_Projetada_Preco_Sugerido": "Venda Projetada Preço Sugerido",
            "Ganho_Unitario": "Ganho Unitário",
            "Ganho_Potencial_Simulador": "Ganho Produto",
            "Menor_Preco": "Menor Preço",
            "Loja_Menor_Preco_Concorrente": "Loja Menor Preço Concorrente",
            "Qtd_Vendida_Mes_Anterior": "Qtd Vendida Mês Anterior",
            "Preco_Medio": "Preço Médio",
            "Margem_%": "Margem %",
            "Margem_%_Menor_Preco": "Margem % Menor Preço",
            "Lucro_Unitario": "Lucro Unitário"
        }
    )

    # Ordem oficial das colunas na tabela de produtos da recomendação
    colunas_exibicao = [
        "EAN",
        "Produto",
        "Laboratório",
        "Família",
        "CURVA",
        "Recomendacao",
        "Qtd Vendida Mês Anterior",
        "Venda Preço Antigo",
        "Venda Projetada Preço Sugerido",
        "Custo",
        "Preço Atual",
        "Preço Sugerido Mercado",
        "Preço Médio",
        "Menor Preço",
        "Margem % Menor Preço",
        "Margem %",
        "Loja Menor Preço Concorrente",
        "Lucro Unitário",
        "Ganho Unitário",
        "Ganho Produto"
    ]

    produtos_exibir = produtos_exibir[
        [c for c in colunas_exibicao if c in produtos_exibir.columns]
    ]

    st.dataframe(
        produtos_exibir,
        use_container_width=True,
        hide_index=True,
        height=420
    )

    # --------------------------------------------------
    # EXPORTAÇÃO DA RECOMENDAÇÃO
    # --------------------------------------------------

    exportar_recomendacao = produtos_detalhe[colunas_exibir].copy()

    # Nova coluna na exportação: Margem considerando seguir o menor preço do mercado.
    # IMPORTANTE: mantém a coluna original Margem_% sem alteração.
    if "Custo" in exportar_recomendacao.columns and "Menor_Preco" in exportar_recomendacao.columns:
        custo_num = pd.to_numeric(exportar_recomendacao["Custo"], errors="coerce")
        menor_preco_num = pd.to_numeric(exportar_recomendacao["Menor_Preco"], errors="coerce")
        exportar_recomendacao["Margem_%_Menor_Preco"] = np.where(
            menor_preco_num > 0,
            ((menor_preco_num - custo_num) / menor_preco_num) * 100,
            np.nan
        )

    for coluna in [
        "Venda_Preco_Antigo",
        "Venda_Projetada_Preco_Sugerido",
        "Custo",
        "Preco_Atual",
        "Preco_Sugerido_Mercado",
        "Ganho_Unitario",
        "Ganho_Potencial_Simulador",
        "Menor_Preco",
        "Lucro_Unitario",
        "Preco_Medio"
    ]:

        if coluna in exportar_recomendacao.columns:
            exportar_recomendacao[coluna] = exportar_recomendacao[coluna].apply(moeda_br)

    if "Margem_%" in exportar_recomendacao.columns:
        exportar_recomendacao["Margem_%"] = exportar_recomendacao["Margem_%"].apply(percentual_br)

    if "Margem_%_Menor_Preco" in exportar_recomendacao.columns:
        exportar_recomendacao["Margem_%_Menor_Preco"] = exportar_recomendacao["Margem_%_Menor_Preco"].apply(percentual_br)

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

    exportar_recomendacao = exportar_recomendacao.rename(
        columns={
            "Preco_Atual": "Preço Atual",
            "Preco_Sugerido_Mercado": "Preço Sugerido Mercado",
            "Venda_Preco_Antigo": "Venda Preço Antigo",
            "Venda_Projetada_Preco_Sugerido": "Venda Projetada Preço Sugerido",
            "Ganho_Unitario": "Ganho Unitário",
            "Ganho_Potencial_Simulador": "Ganho Produto",
            "Menor_Preco": "Menor Preço",
            "Loja_Menor_Preco_Concorrente": "Loja Menor Preço Concorrente",
            "Qtd_Vendida_Mes_Anterior": "Qtd Vendida Mês Anterior",
            "Preco_Medio": "Preço Médio",
            "Margem_%": "Margem %",
            "Margem_%_Menor_Preco": "Margem % Menor Preço",
            "Lucro_Unitario": "Lucro Unitário"
        }
    )

    # Exportação na mesma ordem oficial da tela
    exportar_recomendacao = exportar_recomendacao[
        [c for c in colunas_exibicao if c in exportar_recomendacao.columns]
    ]

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



# CURVA ABC
# --------------------------------------------------

st.subheader(
    "📈 Curva ABC"
)

explicacao_calculo(
    "Curva ABC do ganho potencial",
    [
        "Os produtos são ordenados do maior para o menor Ganho_Potencial.",
        "Perc_Acum representa a participação acumulada do ganho potencial no total filtrado.",
        "Classe A concentra aproximadamente os maiores impactos financeiros; B representa impacto intermediário; C representa menor impacto.",
        "Menor Preço, Rede, Farmácia e Data vêm do histórico de pesquisa, buscando o menor preço concorrente por produto."
    ]
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
                "Rede": "Rede_Menor_Preco_Concorrente",
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
    "Rede_Menor_Preco_Concorrente",
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
            "Rede_Menor_Preco_Concorrente",
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

explicacao_calculo(
    "Top oportunidades",
    [
        "A lista é ordenada pela coluna Ganho_Potencial em ordem decrescente.",
        "Os primeiros produtos são os que oferecem maior oportunidade financeira estimada dentro dos filtros aplicados.",
        "Margem, lucro unitário e preço médio são exibidos apenas quando essas colunas existem na base."
    ]
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
# MAPA DE CALOR - MARCAS E BAIRROS POR QUANTIDADE DE PESQUISAS
# --------------------------------------------------

st.subheader(
    "🔥 Mapa de calor"
)

explicacao_calculo(
    "Mapa de calor",
    [
        "Por marca/família: conta a quantidade de pesquisas por Família e exibe as 40 maiores.",
        "Por bairro: conta a quantidade de pesquisas por Bairro e exibe os 40 maiores.",
        "A intensidade visual aumenta conforme a quantidade de pesquisas encontradas."
    ]
)

# --------------------------------------------------
# MAPA DE CALOR POR MARCA
# --------------------------------------------------

if "Família" in df_filtrado.columns:

    heat_marcas = (
        df_filtrado
        .groupby("Família")
        .size()
        .reset_index(name="Quantidade_Pesquisas")
        .sort_values(
            "Quantidade_Pesquisas",
            ascending=False
        )
        .head(40)
    )

    heat_marcas["Grupo"] = "Marcas"

    heat_pivot = heat_marcas.pivot_table(
        values="Quantidade_Pesquisas",
        index="Grupo",
        columns="Família",
        aggfunc="sum",
        fill_value=0
    )

    fig = px.imshow(
        heat_pivot,
        aspect="auto",
        text_auto=True,
        labels={
            "x": "Marca",
            "y": "",
            "color": "Quantidade de Pesquisas"
        },
        title="Top 40 Marcas por Quantidade de Pesquisas"
    )

    fig.update_layout(
        height=420,
        xaxis_tickangle=-90,
        margin={
            "l": 20,
            "r": 20,
            "t": 60,
            "b": 120
        }
    )

    st.plotly_chart(
        fig,
        width="stretch",
        key="heatmap_marcas_quantidade"
    )

else:

    st.warning(
        "A coluna Família/Marca não foi encontrada para montar o mapa de calor por marca."
    )

# --------------------------------------------------
# MAPA DE CALOR POR BAIRRO
# --------------------------------------------------

if (
    not historico.empty
    and "Bairro" in historico.columns
):

    heat_bairros = (
        historico
        .dropna(
            subset=[
                "Bairro"
            ]
        )
        .groupby("Bairro")
        .size()
        .reset_index(name="Quantidade_Pesquisas")
        .sort_values(
            "Quantidade_Pesquisas",
            ascending=False
        )
        .head(40)
    )

    heat_bairros["Grupo"] = "Bairros"

    heat_bairros_pivot = heat_bairros.pivot_table(
        values="Quantidade_Pesquisas",
        index="Grupo",
        columns="Bairro",
        aggfunc="sum",
        fill_value=0
    )

    fig_bairro = px.imshow(
        heat_bairros_pivot,
        aspect="auto",
        text_auto=True,
        labels={
            "x": "Bairro",
            "y": "",
            "color": "Quantidade de Pesquisas"
        },
        title="Top 40 Bairros por Quantidade de Pesquisas"
    )

    fig_bairro.update_layout(
        height=420,
        xaxis_tickangle=-90,
        margin={
            "l": 20,
            "r": 20,
            "t": 60,
            "b": 120
        }
    )

    st.plotly_chart(
        fig_bairro,
        width="stretch",
        key="heatmap_bairros_quantidade"
    )

else:

    st.warning(
        "A coluna Bairro não foi encontrada para montar o mapa de calor por bairro."
    )

# --------------------------------------------------
# HISTÓRICO
# --------------------------------------------------

if not historico.empty:

    st.subheader("📈 Evolução Histórica")

    explicacao_calculo(
        "Evolução histórica",
        [
            "O gráfico filtra um produto/EAN e acompanha a variação do Preço (R$) ao longo da Data Emissão.",
            "Cada linha representa uma farmácia pesquisada.",
            "O rótulo de preço aparece no último ponto de cada farmácia para reduzir poluição visual."
        ]
    )

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

        # --------------------------------------------------
        # RÓTULOS SEM SOBREPOSIÇÃO
        # --------------------------------------------------

        hist = hist.sort_values(
            [
                "Farmácia",
                "Data Emissão"
            ]
        ).copy()

        hist["Preço_Label"] = ""

        # Mostrar rótulo somente no último ponto de cada farmácia
        idx_ultimo_ponto = (
            hist
            .groupby("Farmácia")
            ["Data Emissão"]
            .idxmax()
        )

        hist.loc[
            idx_ultimo_ponto,
            "Preço_Label"
        ] = (
            hist.loc[
                idx_ultimo_ponto,
                "Preço (R$)"
            ]
            .apply(moeda_br)
        )

        # Se os últimos preços estiverem muito próximos, oculta rótulos repetidos/próximos
        ultimos = (
            hist
            .loc[idx_ultimo_ponto]
            .sort_values("Preço (R$)")
            .copy()
        )

        ultimo_preco_exibido = None

        for idx in ultimos.index:

            preco_atual = ultimos.loc[
                idx,
                "Preço (R$)"
            ]

            if (
                ultimo_preco_exibido is not None
                and abs(preco_atual - ultimo_preco_exibido) < 0.75
            ):

                hist.loc[
                    idx,
                    "Preço_Label"
                ] = ""

            else:

                ultimo_preco_exibido = preco_atual

        fig = px.line(
            hist,
            x="Data Emissão",
            y="Preço (R$)",
            color="Farmácia",
            markers=True,
            text="Preço_Label"
        )

        fig.update_traces(
            mode="lines+markers+text",
            marker={
                "size": 6
            },
            textposition="top center",
            textfont={
                "size": 10
            }
        )

        fig.update_layout(
            yaxis_title="Preço (R$)",
            xaxis_title="Data Emissão"
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
    and "lat" in historico.columns
    and "lon" in historico.columns
):

    st.subheader(
        "🗺️ Mapa Farmácias"
    )

    explicacao_calculo(
        "Mapa de farmácias",
        [
            "Cada ponto usa as colunas lat e lon do histórico de pesquisa.",
            "A classificação da loja é feita pelo nome da farmácia: concorrência, Zanol e Thomaz ou Triangulo Drogaria.",
            "O zoom inicial é calculado pela dispersão das coordenadas encontradas."
        ]
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

    if not mapa_df.empty:

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

        if "Preço (R$)" in mapa_df.columns:

            mapa_df["Preço (R$)"] = (
                pd.to_numeric(
                    mapa_df["Preço (R$)"],
                    errors="coerce"
                )
                .round(2)
            )

        centro_lat = mapa_df["lat"].mean()
        centro_lon = mapa_df["lon"].mean()

        lat_range = mapa_df["lat"].max() - mapa_df["lat"].min()
        lon_range = mapa_df["lon"].max() - mapa_df["lon"].min()

        maior_range = max(
            lat_range,
            lon_range
        )

        if maior_range < 0.03:
            zoom_mapa = 12

        elif maior_range < 0.08:
            zoom_mapa = 11

        elif maior_range < 0.20:
            zoom_mapa = 10

        else:
            zoom_mapa = 9

        hover_cols = []

        for coluna in [
            "Rede",
            "Produto",
            "Preço (R$)",
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
                "Concorrência": "#ff3b30",
                "Zanol e Thomaz": "#ffd60a",
                "Triangulo Drogaria": "#0a84ff"
            },
            hover_name="Farmácia" if "Farmácia" in mapa_df.columns else None,
            hover_data=hover_cols,
            zoom=zoom_mapa,
            center={
                "lat": centro_lat,
                "lon": centro_lon
            },
            height=650
        )

        fig_mapa.update_traces(
            marker={
                "size": 11,
                "opacity": 0.88
            }
        )

        fig_mapa.update_layout(
            mapbox_style="carto-darkmatter",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin={
                "r": 0,
                "t": 10,
                "l": 0,
                "b": 0
            },
            legend={
                "title": {
                    "text": "Tipo de Loja"
                },
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "right",
                "x": 1
            }
        )

        st.plotly_chart(
            fig_mapa,
            width="stretch",
            key="mapa_farmacias_cores"
        )

    else:

        st.info(
            "Não há coordenadas válidas para exibir no mapa."
        )

# --------------------------------------------------
# MONITORAMENTO POR REDE
# --------------------------------------------------

if (
    not historico.empty
    and "Farmácia" in historico.columns
    and "Preço (R$)" in historico.columns
):

    st.subheader("🏪 Monitoramento por Rede")

    explicacao_calculo(
        "Monitoramento por rede",
        [
            "A rede é identificada a partir do nome da farmácia.",
            "Quantidade de Pesquisas = contagem de preços coletados por rede.",
            "Preço Médio = média da coluna Preço (R$) por rede."
        ]
    )

    historico["Rede"] = (
        historico["Farmácia"]
        .apply(identificar_rede)
    )

    historico["Preço (R$)"] = pd.to_numeric(
        historico["Preço (R$)"],
        errors="coerce"
    )

    rede_df = (
        historico
        .groupby("Rede")
        .agg(
            Preco_Medio=("Preço (R$)", "mean"),
            Quantidade_Pesquisas=("Preço (R$)", "count")
        )
        .reset_index()
    )

    rede_df["Preco_Medio"] = (
        rede_df["Preco_Medio"]
        .round(2)
    )

    rede_df = rede_df.sort_values(
        "Quantidade_Pesquisas",
        ascending=False
    )

    rede_grafico = (
        rede_df
        .head(30)
        .copy()
    )

    fig = px.bar(
        rede_grafico,
        x="Rede",
        y="Quantidade_Pesquisas",
        text="Quantidade_Pesquisas",
        title="Top 30 Redes por Quantidade de Pesquisas"
    )

    fig.update_traces(
        textposition="outside"
    )

    fig.update_layout(
        xaxis_title="Rede",
        yaxis_title="Quantidade de Pesquisas"
    )

    st.plotly_chart(
        fig,
        width="stretch",
        key="monitoramento_rede"
    )

# --------------------------------------------------
# RANKING CONCORRENTES
# --------------------------------------------------

if (
    not historico.empty
    and "Farmácia" in historico.columns
    and "Preço (R$)" in historico.columns
):

    st.subheader(
        "🏆 Ranking Concorrentes"
    )

    explicacao_calculo(
        "Ranking de concorrentes",
        [
            "O ranking agrupa o histórico por Farmácia.",
            "Quantidade de Pesquisas = número de registros de preço da farmácia.",
            "Preço Médio = média dos preços pesquisados na farmácia.",
            "A ordenação prioriza maior quantidade de pesquisas e, em seguida, menor preço médio."
        ]
    )

    historico["Preço (R$)"] = pd.to_numeric(
        historico["Preço (R$)"],
        errors="coerce"
    )

    ranking = (
        historico
        .groupby("Farmácia")
        .agg(
            Preco_Medio=("Preço (R$)", "mean"),
            Quantidade_Pesquisas=("Preço (R$)", "count")
        )
        .reset_index()
    )

    ranking["Preco_Medio"] = (
        ranking["Preco_Medio"]
        .round(2)
    )

    ranking = ranking.sort_values(
        [
            "Quantidade_Pesquisas",
            "Preco_Medio"
        ],
        ascending=[
            False,
            True
        ]
    )

    ranking_exibir = ranking.copy()

    ranking_exibir["Preco_Medio"] = (
        ranking_exibir["Preco_Medio"]
        .apply(moeda_br)
    )

    ranking_exibir = ranking_exibir.rename(
        columns={
            "Farmácia": "Farmácia",
            "Quantidade_Pesquisas": "Quantidade de Pesquisas",
            "Preco_Medio": "Preço Médio"
        }
    )

    st.dataframe(
        ranking_exibir[
            [
                "Farmácia",
                "Quantidade de Pesquisas",
                "Preço Médio"
            ]
        ],
        width="stretch"
    )

# --------------------------------------------------

# FAMÍLIAS

# --------------------------------------------------

st.subheader(
"💊 Famílias"
)

explicacao_calculo(
    "Famílias",
    [
        "O gráfico soma o Ganho_Potencial por Família.",
        "As famílias são ordenadas do maior para o menor potencial de captura.",
        "A visão ajuda a identificar quais categorias concentram maior oportunidade financeira."
    ]
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

explicacao_calculo(
    "Laboratórios",
    [
        "Ganho_Potencial = soma das oportunidades dos produtos de cada laboratório.",
        "Margem_% = média da margem dos produtos do laboratório.",
        "A tabela é ordenada pelo maior ganho potencial para priorizar negociação e ajuste de preço."
    ]
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

    explicacao_calculo(
        "Curva ABC financeira",
        [
            "A base de compra é ordenada pelo Valor_Liquido em ordem decrescente.",
            "Participação = Valor_Liquido do item dividido pelo total de Valor_Liquido.",
            "Acumulado = soma progressiva da participação.",
            "Classe A vai até 80% acumulado, Classe B de 80% a 95%, e Classe C acima de 95%."
        ]
    )

    # Remover Total Geral definitivamente
    if "Marca" in compra.columns:

        compra = compra[
            ~compra["Marca"]
            .astype(str)
            .str.upper()
            .str.strip()
            .isin(
                [
                    "TOTAL GERAL",
                    "TOTAL",
                    "GRAND TOTAL"
                ]
            )
        ].copy()

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
    "🤖 Índice de Oportunidade Eirox"
)

# Cálculo do índice com tratamento seguro para evitar erro caso alguma coluna não exista.
margem_media_score = 0
if "Margem_%" in df_filtrado.columns:
    margem_media_score = pd.to_numeric(
        df_filtrado["Margem_%"],
        errors="coerce"
    ).dropna().mean()

ganho_potencial_score = 0
if "Ganho_Potencial" in df_filtrado.columns:
    ganho_potencial_score = pd.to_numeric(
        df_filtrado["Ganho_Potencial"],
        errors="coerce"
    ).fillna(0).sum()

score = round(
    (margem_media_score * 0.6)
    +
    ((ganho_potencial_score / 1000) * 0.4)
)

st.metric(
    "Índice Eirox",
    score
)

with st.expander("🎯 Entenda o Índice de Oportunidade Eirox", expanded=False):

    st.markdown("""
### Como funciona o Índice de Oportunidade Eirox?

O Índice Eirox identifica os produtos com maior potencial de geração de resultado através de ações de Pricing.

---

### 💰 Potencial de Captura

Representa o valor adicional que a empresa poderia faturar ao ajustar o preço do produto até o limite competitivo do mercado, sem ficar mais cara que a concorrência.

#### Como calculamos?

**Espaço para aumento = Preço Máximo Competitivo - Preço Atual**

**Potencial de Captura = Espaço para aumento × Quantidade vendida no mês anterior**

#### Exemplo

- Preço Atual: R$ 10,00
- Concorrência: R$ 12,00
- Espaço para aumento: R$ 2,00
- Quantidade vendida no mês anterior: 1.000 unidades

**Potencial de Captura = R$ 2,00 × 1.000 = R$ 2.000**

Ou seja, existe uma oportunidade de gerar aproximadamente **R$ 2.000 adicionais** sem ultrapassar o preço da concorrência.

---

### 📈 Composição do Índice Eirox

**60% → Rentabilidade Atual**

Representa a qualidade da margem do produto.

**40% → Potencial de Captura**

Representa o tamanho financeiro da oportunidade.

#### Fórmula

**Índice Eirox = (Rentabilidade Atual × 60%) + ((Potencial de Captura ÷ 1.000) × 40%)**

---

### Como interpretar?

🟢 **Acima de 70 pontos**

- Produto altamente rentável.
- Grande oportunidade de captura de resultado.

🟡 **Entre 40 e 70 pontos**

- Produto com potencial relevante de otimização.

🔴 **Abaixo de 40 pontos**

- Baixo impacto financeiro para ações de Pricing.

---

### Resumo

Quanto maior o Índice Eirox, maior a combinação entre:

✔ Rentabilidade atual

✔ Espaço para aumento de preço

✔ Potencial financeiro de captura de resultado
""")


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

    explicacao_calculo(
        "Comparativo de redes",
        [
            "O produto é filtrado pelo EAN selecionado.",
            "Preço (R$) = média do preço pesquisado por Rede e Farmácia.",
            "Menor Mercado = menor preço encontrado entre as lojas para o produto.",
            "Dif R$ = preço da loja menos o menor preço de mercado.",
            "Dif % = Dif R$ dividido pelo Menor Mercado."
        ]
    )

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

    # Exibição limpa no gráfico: manter somente o nome da rede,
    # sem concatenar o nome jurídico/farmácia.
    ranking["Loja"] = (
        ranking["Rede"]
        .fillna("")
        .astype(str)
        .str.strip()
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
        xaxis_title="Rede",
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

    # Garante que a tela mostre somente o nome comercial da rede.
    # Se a coluna Rede vier vazia, identifica a rede pela razão social/loja,
    # mas NÃO exibe a coluna de loja na tabela.
    for col_rede_tmp, col_loja_tmp in [
        ("Rede_Preco_Maximo_Competitivo", "Loja_Preco_Maximo_Competitivo"),
        ("Rede_Menor_Preco", "Loja_Menor_Preco"),
    ]:
        if col_rede_tmp in simulacao.columns:
            if col_loja_tmp in simulacao.columns:
                simulacao[col_rede_tmp] = [
                    limpar_nome_rede_eirox(rede, loja)
                    for rede, loja in zip(simulacao[col_rede_tmp], simulacao[col_loja_tmp])
                ]
            else:
                simulacao[col_rede_tmp] = [
                    limpar_nome_rede_eirox(rede, "")
                    for rede in simulacao[col_rede_tmp]
                ]

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
        "Rede_Preco_Maximo_Competitivo",
        "Data_Preco_Maximo_Competitivo",
        "Menor_Preco",
        "Rede_Menor_Preco",
        "Data_Menor_Preco",
        "Venda_Projetada_Preco_Sugerido",
        "Ganho_Unitario",
        "Ganho_Potencial_Simulador"
    ]

    colunas_exibir = [c for c in colunas_exibir if c in simulacao.columns]

    simulacao_exibir = simulacao[colunas_exibir].copy()

    for coluna in [
        "Venda_Preco_Antigo",
        "Preco_Atual",
        "Preco_Sugerido_Mercado",
        "Menor_Preco",
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

    for coluna_data in ["Data_Preco_Maximo_Competitivo", "Data_Menor_Preco"]:
        if coluna_data in simulacao_exibir.columns:
            simulacao_exibir[coluna_data] = simulacao_exibir[coluna_data].apply(data_br)

    simulacao_exibir = simulacao_exibir.rename(columns={
        "Qtd_Vendida_Mes_Anterior": "Qtd Vendida Mês Anterior",
        "Venda_Preco_Antigo": "Venda Preço Antigo",
        "Preco_Atual": "Preço Atual",
        "Preco_Sugerido_Mercado": "Preço Máximo Competitivo",
        "Rede_Preco_Maximo_Competitivo": "Rede Preço Máximo Competitivo",
        "Data_Preco_Maximo_Competitivo": "Data Preço Máximo Competitivo",
        "Menor_Preco": "Menor Preço",
        "Rede_Menor_Preco": "Rede Menor Preço",
        "Data_Menor_Preco": "Data Menor Preço",
        "Venda_Projetada_Preco_Sugerido": "Venda Projetada Preço Sugerido",
        "Ganho_Unitario": "Ganho Unitário",
        "Ganho_Potencial_Simulador": "Ganho Produto"
    })

    st.dataframe(
        simulacao_exibir,
        width="stretch"
    )

    # Gráfico oficial do Dashboard: usa apenas Analise_Pricing.xlsx
    base_ganho_oficial = preparar_ganho_oficial_dashboard(
        df_filtrado
    )

    eixo_produto_grafico = (
        "Produto"
        if "Produto" in base_ganho_oficial.columns
        else "EAN"
    )

    top_ganho_grafico = (
        base_ganho_oficial
        .sort_values(
            "Ganho_Potencial",
            ascending=True
        )
        .tail(20)
        .copy()
    )

    top_ganho_grafico["Ganho_Label"] = (
        top_ganho_grafico["Ganho_Potencial"]
        .apply(moeda_br)
    )

    fig = px.bar(
        top_ganho_grafico,
        x="Ganho_Potencial",
        y=eixo_produto_grafico,
        orientation="h",
        text="Ganho_Label",
        title="Top 20 Produtos com Maior Ganho Projetado",
        labels={
            "Ganho_Potencial": "Ganho Projetado",
            eixo_produto_grafico: "Produto"
        }
    )

    fig.update_traces(
        textposition="outside",
        cliponaxis=False
    )

    fig.update_layout(
        height=650,
        margin=dict(
            l=20,
            r=180,
            t=60,
            b=40
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            tickformat=",",
            showgrid=True
        ),
        yaxis=dict(
            automargin=True
        )
    )

    st.plotly_chart(
        fig,
        width="stretch",
        key="dashboard_ganho_oficial"
    )

else:

    pass


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
