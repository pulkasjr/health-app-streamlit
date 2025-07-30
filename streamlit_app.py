# streamlit_app.py (Versão com Gráficos do Google Fit)
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
    "https://www.googleapis.com/auth/fitness.blood_pressure.read",
    "https://www.googleapis.com/auth/fitness.blood_glucose.read",
    "https://www.googleapis.com/auth/fitness.heart_rate.read",
    "https://www.googleapis.com/auth/fitness.sleep.read"
]

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

# ----- FUNÇÃO DE BUSCA NO GOOGLE FIT (APRIMORADA) -----
def buscar_dados_google_fit():
    token = obter_token_fit(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_TOKEN_URI, GOOGLE_TOKEN_FILE)
    if not token:
        return None, "Token do Google Fit não encontrado. Por favor, conecte-se."

    headers = {"Authorization": f"Bearer {token['access_token']}"}
    end_time_ns = int(time.time() * 1e9)
    start_time_ns = int((time.time() - 7 * 24 * 60 * 60) * 1e9) # Últimos 7 dias
    dataset_id = f"{start_time_ns}-{end_time_ns}"

    resultados = {}

    # --- Passos ---
    try:
        url_passos = f"https://www.googleapis.com/fitness/v1/users/me/dataSources/derived:com.google.step_count.delta:com.google.android.gms:aggregated/datasets/{dataset_id}"
        r_passos = requests.get(url_passos, headers=headers).json()
        passos_data = [(int(p['startTimeNanos']), p['value'][0]['intVal']) for p in r_passos.get('point', [])]
        df_passos = pd.DataFrame(passos_data, columns=["timestamp_ns", "steps"])
        if not df_passos.empty:
            df_passos["date"] = pd.to_datetime(df_passos["timestamp_ns"]).dt.date
            resultados["passos"] = df_passos.groupby("date")["steps"].sum().reset_index()
        else:
            resultados["passos"] = pd.DataFrame()
    except Exception as e:
        print(f"Erro ao buscar passos: {e}")
        resultados["passos"] = pd.DataFrame()

    # --- Batimentos Cardíacos ---
    try:
        url_hr = f"https://www.googleapis.com/fitness/v1/users/me/dataSources/derived:com.google.heart_rate.bpm:com.google.android.gms:aggregated/datasets/{dataset_id}"
        r_hr = requests.get(url_hr, headers=headers).json()
        bpm_data = [(int(p['startTimeNanos']), p['value'][0]['fpVal']) for p in r_hr.get('point', [])]
        df_bpm = pd.DataFrame(bpm_data, columns=["timestamp_ns", "bpm"])
        if not df_bpm.empty:
            df_bpm["date"] = pd.to_datetime(df_bpm["timestamp_ns"]).dt.date
            resultados["batimentos"] = df_bpm.groupby("date")["bpm"].mean().reset_index()
        else:
            resultados["batimentos"] = pd.DataFrame()
    except Exception as e:
        print(f"Erro ao buscar batimentos: {e}")
        resultados["batimentos"] = pd.DataFrame()
        
    # --- Sono ---
    try:
        url_sono = f"https://www.googleapis.com/fitness/v1/users/me/dataSources/derived:com.google.sleep.segment:com.google.android.gms:aggregated/datasets/{dataset_id}"
        r_sono = requests.get(url_sono, headers=headers).json()
        sono_data = [(int(p['startTimeNanos']), int(p['endTimeNanos'])) for p in r_sono.get('point', [])]
        df_sono = pd.DataFrame(sono_data, columns=["start_ns", "end_ns"])
        if not df_sono.empty:
            df_sono["date"] = (pd.to_datetime(df_sono["start_ns"]) - pd.Timedelta(hours=4)).dt.date
            df_sono["minutes"] = (df_sono["end_ns"] - df_sono["start_ns"]) / 1e9 / 60
            resultados["sono"] = df_sono.groupby("date")["minutes"].sum().reset_index()
        else:
            resultados["sono"] = pd.DataFrame()
    except Exception as e:
        print(f"Erro ao buscar sono: {e}")
        resultados["sono"] = pd.DataFrame()

    return resultados, None

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
    st.sidebar.markdown(f'<a href="{STRAVA_AUTH_URL}" target="_self">Conectar com Strava</a>', unsafe_allow_html=True)

# Conexão Google Fit
token_google = obter_token_fit(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_TOKEN_URI, GOOGLE_TOKEN_FILE)
if token_google:
    st.sidebar.success("✅ Conectado ao Google Fit")
else:
    st.sidebar.warning("🔴 Não conectado ao Google Fit")
    flow = Flow.from_client_config(client_config_google, scopes=GOOGLE_SCOPES, redirect_uri=GOOGLE_REDIRECT_URI)
    auth_url, _ = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    st.sidebar.markdown(f'<a href="{auth_url}" target="_self">Conectar com Google</a>', unsafe_allow_html=True)

# --- PÁGINA PRINCIPAL ---
st.title("🏥 Painel de Saúde Integrado")

tab1, tab2 = st.tabs(["Meu Histórico Manual", "Dados Automáticos (Google Fit)"])

with tab1:
    with st.expander("➕ Adicionar Novo Registro de Peso e Altura"):
        with st.form("formulario_imc", clear_on_submit=True):
            peso = st.number_input("Peso (kg)", min_value=20.0, max_value=300.0, step=0.1, format="%.2f")
            altura = st.number_input("Altura (m)", min_value=1.0, max_value=2.5, step=0.01, format="%.2f")
            enviado = st.form_submit_button("Salvar e Calcular IMC")
            if enviado and altura > 0:
                imc = round(peso / (altura ** 2), 2)
                salvar_dado(peso, altura, imc)
                st.success(f"IMC calculado: {imc} — dados salvos!")
            elif enviado:
                st.error("A altura deve ser maior que zero.")
    
    st.subheader("📜 Histórico e Evolução do IMC")
    df_local = buscar_dados_locais()
    if not df_local.empty:
        st.dataframe(df_local[['timestamp', 'peso_kg', 'altura_m', 'imc']].rename(columns={'timestamp':'Data', 'peso_kg':'Peso (kg)', 'altura_m':'Altura (m)', 'imc':'IMC'}))
        fig = px.line(df_local.sort_values("timestamp"), x="timestamp", y="imc", title="Evolução do IMC", markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhum dado de IMC armazenado ainda.")

with tab2:
    st.subheader("📱 Dados do Google Fit (Últimos 7 dias)")
    if token_google:
        with st.spinner("Buscando dados do Google Fit... Isso pode levar um momento."):
            dados_fit, erro = buscar_dados_google_fit()
        
        if erro:
            st.error(erro)
        elif dados_fit:
            if not dados_fit["passos"].empty:
                st.subheader("🚶 Passos por dia")
                fig_passos = px.bar(dados_fit["passos"], x="date", y="steps", title="Total de Passos por Dia")
                st.plotly_chart(fig_passos, use_container_width=True)
            else:
                st.info("Nenhum dado de passos encontrado.")
            
            if not dados_fit["batimentos"].empty:
                st.subheader("❤️ Batimentos Cardíacos (Média Diária)")
                fig_bpm = px.line(dados_fit["batimentos"], x="date", y="bpm", title="Média de BPM por Dia", markers=True)
                st.plotly_chart(fig_bpm, use_container_width=True)
            else:
                st.info("Nenhum dado de batimentos cardíacos encontrado.")
            
            if not dados_fit["sono"].empty:
                st.subheader("😴 Minutos de Sono por Noite")
                fig_sono = px.bar(dados_fit["sono"], x="date", y="minutes", title="Total de Minutos de Sono por Noite")
                st.plotly_chart(fig_sono, use_container_width=True)
            else:
                st.info("Nenhum dado de sono encontrado.")
    else:
        st.info("Conecte sua conta do Google Fit na barra lateral para ver os dados automáticos.")
        #git