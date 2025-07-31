# streamlit_app.py (VERSÃO FINAL PARA RENDER)
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

# Importando as funções dos módulos utils
from utils.strava_tokens import obter_token_valido as obter_token_strava, salvar_tokens as salvar_tokens_strava
from utils.fit_tokens import obter_token_valido as obter_token_fit, salvar_tokens as salvar_tokens_fit

# ----- CONFIGURAÇÃO CENTRALIZADA (COLOQUE SUAS CREDENCIAIS CORRETAS AQUI) -----
# --- Credenciais do Strava ---
STRAVA_CLIENT_ID = "168833"
STRAVA_CLIENT_SECRET = "6e774fa2c3c62214ea196fbcdf8162a00e58a882"
# --- Endereço para o site online NO RENDER ---
STRAVA_REDIRECT_URI = "https://health-app-streamlit.onrender.com"
STRAVA_TOKEN_FILE = "strava_tokens.json"

# --- Credenciais do Google ---
GOOGLE_CLIENT_ID = "423426384359-m0pr10393ve0seul953bh63lhobqgl2v.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"
# --- Endereço para o site online NO RENDER ---
GOOGLE_REDIRECT_URI = "https://health-app-streamlit.onrender.com"
GOOGLE_TOKEN_FILE = "google_fit_tokens.json"
GOOGLE_TOKEN_URI = 'https://oauth2.googleapis.com/token'
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/fitness.activity.read", "https://www.googleapis.com/auth/fitness.body.read"]

# --- Construção dos objetos de configuração ---
client_config_google = {"web": {"client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET, "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": GOOGLE_TOKEN_URI, "redirect_uris": [GOOGLE_REDIRECT_URI]}}
STRAVA_AUTH_URL = (f"https://www.strava.com/oauth/authorize?client_id={STRAVA_CLIENT_ID}&response_type=code&redirect_uri={STRAVA_REDIRECT_URI}&approval_prompt=force&scope=read_all,activity:read_all")
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"

# ----- BANCO DE DADOS -----
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
    conn = sqlite3.connect("health_data.db")
    df = pd.read_sql_query("SELECT * FROM health_records ORDER BY timestamp DESC", conn, parse_dates=["timestamp"])
    conn.close()
    return df

# ----- LÓGICA DO STREAMLIT -----
st.set_page_config(page_title="Painel de Saúde", layout="wide")
init_db()

# --- LÓGICA DE AUTENTICAÇÃO (CALLBACK) ---
query_params = st.query_params
auth_code = query_params.get("code")
scope_param = query_params.get("scope")

if auth_code and 'auth_flow' not in st.session_state:
    st.session_state['auth_flow'] = True
    
    if scope_param and "activity:read_all" in scope_param:
        try:
            with st.spinner("Autorizando Strava..."):
                response = requests.post(STRAVA_TOKEN_URL, data={'client_id': STRAVA_CLIENT_ID, 'client_secret': STRAVA_CLIENT_SECRET, 'code': auth_code, 'grant_type': 'authorization_code'})
                response.raise_for_status()
                salvar_tokens_strava(response.json(), STRAVA_TOKEN_FILE)
                st.success("Strava autorizado com sucesso! Recarregando...")
                time.sleep(1)
                st.query_params.clear()
        except Exception as e:
            st.error(f"Erro na autorização do Strava: {e}")
            
    elif scope_param and "googleapis.com" in scope_param:
        try:
            with st.spinner("Autorizando Google Fit..."):
                flow = Flow.from_client_config(client_config_google, scopes=GOOGLE_SCOPES, redirect_uri=GOOGLE_REDIRECT_URI)
                flow.fetch_token(code=auth_code)
                cred = flow.credentials
                tokens = {'access_token': cred.token, 'refresh_token': cred.refresh_token, 'token_uri': cred.token_uri, 'client_id': cred.client_id, 'client_secret': cred.client_secret, 'scopes': cred.scopes, 'expires_at': cred.expiry.timestamp() if cred.expiry else None}
                salvar_tokens_fit(tokens, GOOGLE_TOKEN_FILE)
                st.success("Google Fit autorizado com sucesso! Recarregando...")
                time.sleep(1)
                st.query_params.clear()
        except Exception as e:
            st.error(f"Erro na autorização do Google: {e}")

# --- BARRA LATERAL (SIDEBAR) ---
st.sidebar.title("VidaCheck Saúde")

# Conexão Strava
token_strava = obter_token_strava(STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_TOKEN_FILE)
if token_strava:
    st.sidebar.success("✅ Conectado ao Strava")
else:
    st.sidebar.warning("🔴 Não conectado ao Strava")
    st.sidebar.markdown(f'<a href="{STRAVA_AUTH_URL}" target="_self" style="text-decoration:none; color:inherit;">Conectar com Strava</a>', unsafe_allow_html=True)

# Conexão Google Fit
token_google = obter_token_fit(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_TOKEN_URI, GOOGLE_TOKEN_FILE)
if token_google:
    st.sidebar.success("✅ Conectado ao Google Fit")
else:
    st.sidebar.warning("🔴 Não conectado ao Google Fit")
    flow = Flow.from_client_config(client_config_google, scopes=GOOGLE_SCOPES, redirect_uri=GOOGLE_REDIRECT_URI)
    auth_url, _ = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    st.sidebar.markdown(f'<a href="{auth_url}" target="_self" style="text-decoration:none; color:inherit;">Conectar com Google</a>', unsafe_allow_html=True)

# --- PÁGINA PRINCIPAL ---
st.title("🏥 Painel de Saúde Integrado")

# FORMULÁRIO DE ENTRADA MANUAL
with st.expander("➕ Adicionar Novo Registro de Peso e Altura"):
    with st.form("formulario_imc", clear_on_submit=True):
        peso = st.number_input("Peso (kg)", min_value=20.0, max_value=300.0, step=0.1, format="%.2f")
        altura = st.number_input("Altura (m)", min_value=1.0, max_value=2.5, step=0.01, format="%.2f")
        enviado = st.form_submit_button("Salvar e Calcular IMC")

        if enviado and altura > 0:
            imc = round(peso / (altura ** 2), 2)
            salvar_dado(peso, altura, imc)
            st.success(f"IMC calculado: {imc} — dados salvos!")
            # st.experimental_rerun() # Opcional: recarrega a página para atualizar o gráfico
        elif enviado:
            st.error("A altura deve ser maior que zero.")

# VISUALIZAÇÃO DOS DADOS
df_local = buscar_dados_locais()
if not df_local.empty:
    st.subheader("📜 Histórico e Evolução do IMC")
    st.dataframe(df_local[['timestamp', 'peso_kg', 'altura_m', 'imc']].rename(columns={'timestamp':'Data', 'peso_kg':'Peso (kg)', 'altura_m':'Altura (m)', 'imc':'IMC'}))
    fig = px.line(df_local.sort_values("timestamp"), x="timestamp", y="imc", title="Evolução do IMC", markers=True)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nenhum dado de IMC armazenado ainda. Adicione um registro acima.")