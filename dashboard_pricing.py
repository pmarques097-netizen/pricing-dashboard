import streamlit as st
import os
import pandas as pd
import plotly.express as px
import hashlib
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path


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
        "🔎 Análise por Rede/Loja",
        "🛒 Negociação Compras",
        "🚨 Central de Alertas"
    ],
    "Pricing": [
        "📊 Dashboard Geral",
        "🔎 Análise por Rede/Loja",
        "🛒 Negociação Compras",
        "🚨 Central de Alertas"
    ],
    "Comercial": [
        "📊 Dashboard Geral",
        "🔎 Análise por Rede/Loja",
        "🛒 Negociação Compras",
        "🚨 Central de Alertas"
    ],
    "Regional": [
        "📊 Dashboard Geral",
        "🔎 Análise por Rede/Loja",
        "🛒 Negociação Compras",
        "🚨 Central de Alertas"
    ],
    "Consulta": [
        "📊 Dashboard Geral"
    ]
}


# --------------------------------------------------
# AUDITORIA DE LOGIN E NOTIFICAÇÃO
# --------------------------------------------------

BASE_DIR_LOGIN = Path(__file__).resolve().parent

ARQUIVO_LOG_ACESSO = (
    BASE_DIR_LOGIN / "logs_acesso.csv"
)

LOGIN_EMAIL_DESTINO = os.getenv(
    "LOGIN_EMAIL_DESTINO",
    "pmarques097@gmail.com,paulomarquesintedados@gmail.com"
)

LOGIN_SMTP_HOST = os.getenv(
    "SMTP_HOST",
    "smtp.gmail.com"
)

LOGIN_SMTP_PORT = int(
    os.getenv(
        "SMTP_PORT",
        "465"
    )
)

LOGIN_SMTP_USER = os.getenv(
    "SMTP_USER",
    ""
)

LOGIN_SMTP_PASSWORD = os.getenv(
    "SMTP_PASSWORD",
    ""
)


def registrar_acesso(
    usuario,
    nome,
    perfil
):

    agora = datetime.now()

    novo_log = pd.DataFrame(
        [
            {
                "Data_Hora": agora.strftime("%d/%m/%Y %H:%M:%S"),
                "Usuario": usuario,
                "Nome": nome,
                "Perfil": perfil
            }
        ]
    )

    if ARQUIVO_LOG_ACESSO.exists():

        try:

            log_atual = pd.read_csv(
                ARQUIVO_LOG_ACESSO,
                sep=";",
                encoding="utf-8-sig"
            )

            log_final = pd.concat(
                [
                    log_atual,
                    novo_log
                ],
                ignore_index=True
            )

        except Exception:

            log_final = novo_log

    else:

        log_final = novo_log

    log_final.to_csv(
        ARQUIVO_LOG_ACESSO,
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    return log_final


def montar_html_login(
    usuario,
    nome,
    perfil,
    log_final
):

    agora = datetime.now().strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    total_acessos = len(log_final)

    ultimos = (
        log_final
        .tail(20)
        .copy()
    )

    tabela_html = ultimos.to_html(
        index=False,
        escape=False
    )

    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>🔐 Novo acesso ao Dashboard Eirox</h2>

            <p>Um usuário acabou de acessar a plataforma.</p>

            <table style="border-collapse: collapse; margin-bottom: 20px;">
                <tr>
                    <td style="border:1px solid #ddd; padding:8px;"><b>Data/Hora</b></td>
                    <td style="border:1px solid #ddd; padding:8px;">{agora}</td>
                </tr>
                <tr>
                    <td style="border:1px solid #ddd; padding:8px;"><b>Usuário</b></td>
                    <td style="border:1px solid #ddd; padding:8px;">{usuario}</td>
                </tr>
                <tr>
                    <td style="border:1px solid #ddd; padding:8px;"><b>Nome</b></td>
                    <td style="border:1px solid #ddd; padding:8px;">{nome}</td>
                </tr>
                <tr>
                    <td style="border:1px solid #ddd; padding:8px;"><b>Perfil</b></td>
                    <td style="border:1px solid #ddd; padding:8px;">{perfil}</td>
                </tr>
                <tr>
                    <td style="border:1px solid #ddd; padding:8px;"><b>Total de acessos registrados</b></td>
                    <td style="border:1px solid #ddd; padding:8px;">{total_acessos}</td>
                </tr>
            </table>

            <h3>Últimos 20 acessos</h3>

            {tabela_html}

            <p style="font-size:12px; color:#777;">
                Este e-mail foi gerado automaticamente pela auditoria de login do Dashboard Eirox.
            </p>
        </body>
    </html>
    """

    return html


def enviar_email_login(
    usuario,
    nome,
    perfil,
    log_final
):

    if (
        not LOGIN_EMAIL_DESTINO
        or not LOGIN_SMTP_USER
        or not LOGIN_SMTP_PASSWORD
    ):

        return

    destinatarios = [
        email.strip()
        for email in LOGIN_EMAIL_DESTINO.split(",")
        if email.strip()
    ]

    if not destinatarios:

        return

    agora = datetime.now().strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    msg = EmailMessage()

    msg["Subject"] = (
        f"🔐 Login no Dashboard Eirox - {usuario} - {agora}"
    )

    msg["From"] = LOGIN_SMTP_USER
    msg["To"] = ", ".join(
        destinatarios
    )

    msg.set_content(
        f"O usuário {usuario} acessou o Dashboard Eirox em {agora}."
    )

    msg.add_alternative(
        montar_html_login(
            usuario,
            nome,
            perfil,
            log_final
        ),
        subtype="html"
    )

    if ARQUIVO_LOG_ACESSO.exists():

        with open(
            ARQUIVO_LOG_ACESSO,
            "rb"
        ) as arquivo:

            msg.add_attachment(
                arquivo.read(),
                maintype="text",
                subtype="csv",
                filename="logs_acesso_dashboard_eirox.csv"
            )

    contexto = ssl.create_default_context()

    with smtplib.SMTP_SSL(
        LOGIN_SMTP_HOST,
        LOGIN_SMTP_PORT,
        context=contexto
    ) as servidor:

        servidor.login(
            LOGIN_SMTP_USER,
            LOGIN_SMTP_PASSWORD
        )

        servidor.send_message(
            msg
        )


def auditar_login(
    usuario,
    nome,
    perfil
):

    log_final = registrar_acesso(
        usuario,
        nome,
        perfil
    )

    try:

        enviar_email_login(
            usuario,
            nome,
            perfil,
            log_final
        )

    except Exception as erro:

        print(
            f"Falha ao enviar e-mail de login: {erro}"
        )



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

            auditar_login(
                usuario_key,
                USUARIOS[usuario_key]["nome"],
                USUARIOS[usuario_key]["perfil"]
            )

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
        width=350
    )

except:
    pass

st.markdown(
    """
    <h1 style='margin-bottom:0px;'>
        📊 Eirox - Ferramenta de Inteligência de Pricing
    </h1>

    <h4 style='
        margin-top:0px;
        color:#B0B0B0;
        font-weight:400;
    '>
        Consulta e comparação de preços concorrência
    </h4>
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
# MENU LATERAL / FILTROS
# --------------------------------------------------

try:

    st.sidebar.image(
        "logo eirox.png",
        width=220
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

paginas_liberadas = PERMISSOES_TELAS.get(
    perfil_usuario,
    [
        "📊 Dashboard Geral"
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
# ANÁLISE POR REDE / LOJA
# --------------------------------------------------

if pagina == "🔎 Análise por Rede/Loja":

    st.subheader(
        "🔎 Análise por Rede/Loja"
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
