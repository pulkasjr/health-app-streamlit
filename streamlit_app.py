# streamlit_app.py
import streamlit as st
import sqlite3
import random
import time
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
from google_auth_oauthlib.flow import Flow
import requests
import os

# --- Importações dos Módulos ---
from utils.dados_strava import obter_token_valido as obter_token_strava, salvar_tokens as salvar_tokens_strava, buscar_ultimas_atividades, gerar_mapa_atividade, buscar_estatisticas_atleta
from utils.dados_google_fit import obter_token_valido as obter_token_fit, salvar_tokens as salvar_tokens_fit, obter_passos_diarios, obter_batimentos_medios, obter_sono, obter_ultimo_peso, obter_ultima_altura
from utils.dados_alimentos import buscar_info_alimento, gerar_dicas_nutricionais

# ----- CONFIGURAÇÃO CENTRALIZADA -----
STRAVA_CLIENT_ID = "168833"
STRAVA_CLIENT_SECRET = "6e774fa2c3c62214ea196fbcdf8162a00e58a882"
STRAVA_REDIRECT_URI = "http://localhost:8501"
STRAVA_TOKEN_FILE = "strava_tokens.json"

GOOGLE_CLIENT_ID = "423426384359-m0pr10393ve0seul953bh63lhobqgl2v.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"
GOOGLE_REDIRECT_URI = "http://localhost:8501"
GOOGLE_TOKEN_FILE = "google_fit_tokens.json"
GOOGLE_TOKEN_URI = 'https://oauth2.googleapis.com/token'
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/fitness.activity.read", 
    "https://www.googleapis.com/auth/fitness.body.read",
    "https://www.googleapis.com/auth/fitness.heart_rate.read",
    "https://www.googleapis.com/auth/fitness.sleep.read"
]

client_config_google = {
    "web": {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": GOOGLE_TOKEN_URI,
        "redirect_uris": [GOOGLE_REDIRECT_URI]
    }
}

STRAVA_AUTH_URL = (f"https://www.strava.com/oauth/authorize?client_id={STRAVA_CLIENT_ID}&response_type=code&redirect_uri={STRAVA_REDIRECT_URI}&approval_prompt=force&scope=read_all,activity:read_all")
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"

# ----- BANCO DE DADOS E FUNÇÕES AUXILIARES -----
def init_db():
    conn = sqlite3.connect("health_data.db")
    conn.execute('''CREATE TABLE IF NOT EXISTS health_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        peso_kg REAL,
                        altura_m REAL,
                        imc REAL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )''')
    conn.commit()
    conn.close()

def salvar_dado(peso, altura, imc):
    conn = sqlite3.connect("health_data.db")
    conn.execute("INSERT INTO health_records (peso_kg, altura_m, imc) VALUES (?, ?, ?)", (peso, altura, imc))
    conn.commit()
    conn.close()

def buscar_dados_locais():
    try:
        conn = sqlite3.connect("health_data.db")
        df = pd.read_sql_query("SELECT * FROM health_records ORDER BY timestamp DESC", conn, parse_dates=["timestamp"])
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def classificar_imc(imc):
    if imc < 18.5: return ("Abaixo do Peso", "🔵")
    elif 18.5 <= imc < 25: return ("Peso Normal", "🟢")
    elif 25 <= imc < 30: return ("Sobrepeso", "🟠")
    elif 30 <= imc < 35: return ("Obesidade Grau I", "🔴")
    elif 35 <= imc < 40: return ("Obesidade Grau II", "🔴")
    else: return ("Obesidade Grau III", "🔴")

# ----- LÓGICA DO STREAMLIT -----
st.set_page_config(page_title="Painel de Saúde", layout="wide")
init_db()

# --- Autenticação (Carrega os tokens salvos) ---
token_strava = obter_token_strava(STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_TOKEN_FILE)
token_google = obter_token_fit(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_TOKEN_URI, GOOGLE_TOKEN_FILE)

# --- Sidebar ---
st.sidebar.title("VidaCheck Saúde")

# Conexão Strava
if token_strava:
    st.sidebar.success("✅ Conectado ao Strava")
else:
    st.sidebar.warning("🔴 Não conectado ao Strava")
    st.sidebar.markdown(f'<a href="{STRAVA_AUTH_URL}" target="_self">Conectar ao Strava</a>', unsafe_allow_html=True)

# Conexão Google Fit
if token_google:
    st.sidebar.success("✅ Conectado ao Google Fit")
else:
    st.sidebar.warning("🔴 Não conectado ao Google Fit")
    flow = Flow.from_client_config(client_config_google, scopes=GOOGLE_SCOPES, redirect_uri=GOOGLE_REDIRECT_URI)
    auth_url, _ = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    st.sidebar.markdown(f'<a href="{auth_url}" target="_self">Conectar ao Google Fit</a>', unsafe_allow_html=True)

# --- Página Principal ---
st.title("🏥 Painel de Saúde Integrado")

# --- Abas ---
tabs = st.tabs(["🧮 IMC & Glicemia", "🧍 Google Fit", "🚴 Strava", "🥗 Alimentos"])

with tabs[0]:
    st.header("🧮 Cálculo do IMC")
    with st.form("form_imc"):
        peso = st.number_input("Peso (kg)", min_value=30.0, max_value=300.0, step=0.1)
        altura = st.number_input("Altura (m)", min_value=1.0, max_value=2.5, step=0.01)
        enviar = st.form_submit_button("Calcular IMC")
        if enviar:
            imc = round(peso / (altura ** 2), 2)
            salvar_dado(peso, altura, imc)
            st.success(f"IMC calculado: {imc}")
            categoria, emoji = classificar_imc(imc)
            st.info(f"{emoji} Classificação: {categoria}")

    df_local = buscar_dados_locais()
    if not df_local.empty:
        st.subheader("Histórico de IMC")
        st.dataframe(df_local[['timestamp', 'peso_kg', 'altura_m', 'imc']])
        fig = px.line(df_local.sort_values("timestamp"), x="timestamp", y="imc", markers=True, title="Evolução do IMC")
        st.plotly_chart(fig, use_container_width=True)

with tabs[1]:
    st.header("🧍 Dados do Google Fit")
    if token_google:
        hoje = datetime.now().date()
        inicio = datetime.combine(hoje - timedelta(days=6), datetime.min.time())
        fim = datetime.combine(hoje, datetime.max.time())

        passos = obter_passos_diarios(token_google, inicio, fim)
        batimentos = obter_batimentos_medios(token_google, inicio, fim)
        sono = obter_sono(token_google, inicio, fim)
        peso = obter_ultimo_peso(token_google)
        altura = obter_ultima_altura(token_google)

        st.subheader("📈 Atividades da Semana")
        st.write("**Passos Diários:**")
        st.bar_chart(pd.Series(passos))

        st.write("**Frequência Cardíaca Média (bpm):**")
        st.line_chart(pd.Series(batimentos))

        st.write("**Horas de Sono:**")
        st.bar_chart(pd.Series(sono))

        if peso: st.write(f"**Peso Atual:** {peso} kg")
        if altura: st.write(f"**Altura Atual:** {altura} m")
    else:
        st.warning("Conecte ao Google Fit para ver seus dados.")

# --- Aba Strava ---
# (Já estava completa)

# --- Aba Alimentos ---
# (Já estava completa)
