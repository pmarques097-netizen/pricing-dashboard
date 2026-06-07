import streamlit as st
import os
import zipfile
import pandas as pd
import plotly.express as px
import plotly.io as pio
import hashlib
from pathlib import Path
from datetime import datetime

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

VERSAO_APP = "ganho_100pct_analise_pricing_20260607"

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

    simulacao["Venda_Preco_Antigo"] = simulacao["Qtd_Vendida_Mes_Anterior"] * simulacao["Preco_Atual"]
    simulacao["Venda_Projetada_Preco_Sugerido"] = simulacao["Qtd_Vendida_Mes_Anterior"] * simulacao["Preco_Sugerido_Mercado"]
    simulacao["Ganho_Unitario"] = simulacao["Preco_Sugerido_Mercado"] - simulacao["Preco_Atual"]
    simulacao["Ganho_Potencial_Simulador"] = simulacao["Venda_Projetada_Preco_Sugerido"] - simulacao["Venda_Preco_Antigo"]

    simulacao = simulacao[simulacao["Ganho_Potencial_Simulador"] > 0].copy()

    for c in [
        "Preco_Atual", "Preco_Sugerido_Mercado", "Ganho_Unitario",
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


PERMISSOES_TELAS = {
    "Diretoria": [
        "📊 Dashboard Geral",
        "🔎 Rede/Loja vs Concorrentes",
        "🛒 Negociação Compras",
        "🚨 Central de Alertas",
        "🧪 Diagnóstico",
        "📈 Simulador Inteligente",
        "🏢 Dashboard Executivo"
    ],
    "Pricing": [
        "📊 Dashboard Geral",
        "🔎 Rede/Loja vs Concorrentes",
        "🛒 Negociação Compras",
        "🚨 Central de Alertas",
        "🧪 Diagnóstico",
        "📈 Simulador Inteligente",
        "🏢 Dashboard Executivo"
    ],
    "Comercial": [
        "📊 Dashboard Geral",
        "🔎 Rede/Loja vs Concorrentes",
        "🛒 Negociação Compras",
        "🚨 Central de Alertas",
        "🧪 Diagnóstico",
        "📈 Simulador Inteligente",
        "🏢 Dashboard Executivo"
    ],
    "Regional": [
        "📊 Dashboard Geral",
        "🔎 Rede/Loja vs Concorrentes",
        "🛒 Negociação Compras",
        "🚨 Central de Alertas",
        "🧪 Diagnóstico",
        "📈 Simulador Inteligente",
        "🏢 Dashboard Executivo"
    ],
    "Consulta": [
        "📊 Dashboard Geral",
        "🏢 Dashboard Executivo"
    ]
}


def autenticar_usuario(usuario, senha):

    usuario = str(usuario).strip().lower()

    if usuario not in USUARIOS:
        return False

    senha_hash = hashlib.sha256(
        str(senha).encode()
    ).hexdigest()

    return senha_hash == USUARIOS[usuario]["senha_hash"]


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

            st.session_state["logado"] = True
            st.session_state["usuario"] = usuario_key
            st.session_state["nome_usuario"] = USUARIOS[usuario_key]["nome"]
            st.session_state["perfil_usuario"] = USUARIOS[usuario_key]["perfil"]

            st.rerun()

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

    st.session_state["logado"] = False
    st.session_state["usuario"] = None
    st.session_state["nome_usuario"] = None
    st.session_state["perfil_usuario"] = None
    st.rerun()


exigir_login()

perfil_usuario = st.session_state.get(
    "perfil_usuario",
    "Consulta"
)

nome_usuario = st.session_state.get(
    "nome_usuario",
    ""
)

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
# GANHO POTENCIAL PADRÃO SIMULADOR
# --------------------------------------------------

def encontrar_coluna_global(base, opcoes):

    for coluna in opcoes:

        if coluna in base.columns:
            return coluna

    return None


simulacao_global = pd.DataFrame()
origem_simulacao_global = "vazia"

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

        origem_simulacao_global = "venda_rede"

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

# Fallback: se a venda final não conseguir montar a simulação,
# usa o histórico apenas como diagnóstico/consulta operacional.
# IMPORTANTE: essa simulação NÃO deve substituir o Ganho_Potencial oficial
# da Analise_Pricing.xlsx, para evitar diferença entre localhost e online.
if simulacao_global.empty and not historico.empty:
    simulacao_global = criar_simulacao_por_historico(historico)
    if not simulacao_global.empty:
        origem_simulacao_global = "historico_pesquisa"

# Ganho_Potencial oficial deve vir apenas da Analise_Pricing.xlsx.
# Não sobrescrever com simulacao_global para evitar diferença localhost x online.
if "Ganho_Potencial" in df.columns:
    df["Ganho_Potencial"] = pd.to_numeric(
        df["Ganho_Potencial"],
        errors="coerce"
    ).fillna(0)
else:
    df["Ganho_Potencial"] = 0

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
    f"Versão: {VERSAO_APP}"
)


paginas_liberadas = PERMISSOES_TELAS.get(
    perfil_usuario,
    [
        "📊 Dashboard Geral",
        "🏢 Dashboard Executivo"
    ]
)

pagina = st.sidebar.radio(
    "Escolha a visão",
    paginas_liberadas,
    key="menu_principal",
    label_visibility="collapsed"
)

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
            # DADOS AUTOMÁTICOS DA BASE PRINCIPAL
            # --------------------------------------------------

            preco_atual_padrao = _primeiro_valor_linha(
                item,
                [
                    "Preco_Medio",
                    "Preço Médio",
                    "Preco_Atual",
                    "Preço Atual",
                    "Preço Venda",
                    "Preco Venda",
                    "Preço (R$)",
                    "Preco (R$)",
                    "Valor Unitário",
                    "Valor Unitario"
                ],
                0.0
            )

            lucro_atual_padrao = _primeiro_valor_linha(
                item,
                [
                    "Lucro_Unitario",
                    "Lucro Unitário",
                    "Lucro Atual"
                ],
                0.0
            )

            margem_atual_padrao = _primeiro_valor_linha(
                item,
                [
                    "Margem_%",
                    "Margem %",
                    "Margem"
                ],
                0.0
            )

            custo_padrao = _primeiro_valor_linha(
                item,
                [
                    "Custo",
                    "Custo Médio",
                    "Custo_Medio",
                    "Custo Unitário",
                    "Custo_Unitario"
                ],
                0.0
            )

            if custo_padrao == 0 and preco_atual_padrao > 0 and lucro_atual_padrao != 0:
                custo_padrao = max(preco_atual_padrao - lucro_atual_padrao, 0)

            if custo_padrao == 0 and preco_atual_padrao > 0 and margem_atual_padrao > 0:
                custo_padrao = preco_atual_padrao * (1 - margem_atual_padrao / 100)

            qtd_padrao = 1.0
            menor_concorrente_padrao = 0.0
            preco_sugerido_padrao = preco_atual_padrao

            # --------------------------------------------------
            # DADOS AUTOMÁTICOS DO SIMULADOR GLOBAL
            # --------------------------------------------------

            if (
                "simulacao_global" in globals()
                and not simulacao_global.empty
                and ean_sim
                and "EAN" in simulacao_global.columns
            ):
                sim_auto = simulacao_global.copy()
                sim_auto["EAN"] = (
                    sim_auto["EAN"]
                    .astype(str)
                    .str.replace(".0", "", regex=False)
                    .str.strip()
                )

                sim_auto = sim_auto[sim_auto["EAN"] == ean_sim]

                if not sim_auto.empty:
                    linha_sim = sim_auto.iloc[0]

                    qtd_padrao = _primeiro_valor_linha(
                        linha_sim,
                        ["Qtd_Vendida_Mes_Anterior"],
                        qtd_padrao
                    )

                    preco_atual_padrao = _primeiro_valor_linha(
                        linha_sim,
                        ["Preco_Atual"],
                        preco_atual_padrao
                    )

                    preco_sugerido_padrao = _primeiro_valor_linha(
                        linha_sim,
                        ["Preco_Sugerido_Mercado"],
                        preco_sugerido_padrao
                    )

            # --------------------------------------------------
            # MENOR PREÇO CONCORRENTE PELO HISTÓRICO
            # --------------------------------------------------

            if (
                not historico.empty
                and ean_sim
            ):
                hist_sim = historico.copy()

                if "EAN" not in hist_sim.columns and "EAN (GTIN)" in hist_sim.columns:
                    hist_sim["EAN"] = hist_sim["EAN (GTIN)"]

                if "EAN" in hist_sim.columns:
                    hist_sim["EAN"] = (
                        hist_sim["EAN"]
                        .astype(str)
                        .str.replace(".0", "", regex=False)
                        .str.strip()
                    )

                if "Preço (R$)" not in hist_sim.columns:
                    for col_preco_alt in [
                        "Preco (R$)",
                        "Preço",
                        "Preco",
                        "Valor",
                        "Valor Unitário",
                        "Valor Unitario"
                    ]:
                        if col_preco_alt in hist_sim.columns:
                            hist_sim["Preço (R$)"] = hist_sim[col_preco_alt]
                            break

                if "Preço (R$)" in hist_sim.columns and "EAN" in hist_sim.columns:
                    hist_sim["Preço (R$)"] = pd.to_numeric(
                        hist_sim["Preço (R$)"],
                        errors="coerce"
                    )

                    hist_ean = hist_sim[hist_sim["EAN"] == ean_sim].copy()

                    if not hist_ean.empty:
                        menor_concorrente_padrao = (
                            hist_ean["Preço (R$)"]
                            .dropna()
                            .min()
                        )

                        if pd.isna(menor_concorrente_padrao):
                            menor_concorrente_padrao = 0.0

            if menor_concorrente_padrao and menor_concorrente_padrao > 0:
                preco_sugerido_padrao = menor_concorrente_padrao

            st.markdown("### 🧾 Produto carregado automaticamente")

            info1, info2, info3, info4 = st.columns(4)

            info1.metric("EAN", ean_sim if ean_sim else "Não informado")
            info2.metric("Preço atual base", moeda_br(preco_atual_padrao))
            info3.metric("Menor concorrente", moeda_br(menor_concorrente_padrao))
            info4.metric("Qtd mês base", numero_br(qtd_padrao))

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

            with c2:
                novo_preco = st.number_input(
                    "Novo preço simulado",
                    min_value=0.0,
                    value=float(preco_sugerido_padrao if preco_sugerido_padrao is not None else (preco_atual_padrao if preco_atual_padrao is not None else 0)),
                    step=0.10,
                    format="%.2f",
                    key=f"sim_novo_preco_{ean_sim}"
                )

            with c3:
                custo = st.number_input(
                    "Custo",
                    min_value=0.0,
                    value=float(custo_padrao if custo_padrao is not None else 0),
                    step=0.10,
                    format="%.2f",
                    key=f"sim_custo_{ean_sim}"
                )

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

            with c6:
                cenario = st.selectbox(
                    "Cenário",
                    [
                        "Manual",
                        "Conservador",
                        "Competitivo",
                        "Agressivo",
                        "Maximizar margem"
                    ],
                    key=f"sim_cenario_{ean_sim}"
                )

            if cenario != "Manual":

                if cenario == "Conservador":
                    novo_preco_calc = preco_atual * 1.03

                elif cenario == "Competitivo" and menor_concorrente > 0:
                    novo_preco_calc = menor_concorrente

                elif cenario == "Agressivo" and menor_concorrente > 0:
                    novo_preco_calc = menor_concorrente * 0.98

                elif cenario == "Maximizar margem":
                    novo_preco_calc = preco_atual * 1.08

                else:
                    novo_preco_calc = novo_preco

                novo_preco = float(novo_preco_calc)

                with c7:
                    st.metric("Preço sugerido", moeda_br(novo_preco))

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
            <p>Resumo estratégico para tomada de decisão: riscos, oportunidades, margem e ganho potencial.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    base_exec = df_filtrado.copy()

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
        "Ganho Potencial",
        moeda_br(ganho_total)
    )

    k3.metric(
        "Margem Média",
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
            "Ganho_Potencial"
        ] if c in top.columns
    ]

    top_exibir = top[cols_top].head(20).copy()

    if "Preco_Medio" in top_exibir.columns:
        top_exibir["Preco_Medio"] = top_exibir["Preco_Medio"].apply(moeda_br)

    if "Margem_%" in top_exibir.columns:
        top_exibir["Margem_%"] = top_exibir["Margem_%"].apply(percentual_br)

    if "Ganho_Potencial" in top_exibir.columns:
        top_exibir["Ganho_Potencial"] = top_exibir["Ganho_Potencial"].apply(moeda_br)

    st.dataframe(
        top_exibir,
        use_container_width=True,
        height=520
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
                    "Ganho_Potencial": "Ganho Potencial",
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
        "Preco_Atual",
        "Preco_Sugerido_Mercado",
        "Venda_Projetada_Preco_Sugerido",
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
        "Menor_Preco",
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
            "Lucro_Unitario": "Lucro Unitário"
        }
    )

    st.dataframe(
        produtos_exibir,
        use_container_width=True,
        height=420
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
        "Menor_Preco",
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
            "Lucro_Unitario": "Lucro Unitário"
        }
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
