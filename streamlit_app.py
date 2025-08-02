# streamlit_app.py
import streamlit as st
import sqlite3
import time
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
from google_auth_oauthlib.flow import Flow
import requests
import os

# --- Módulos personalizados ---
from utils.dados_strava import obter_token_valido as obter_token_strava, salvar_tokens as salvar_tokens_strava, buscar_ultimas_atividades, gerar_mapa_atividade, buscar_estatisticas_atleta
from utils.dados_google_fit import obter_token_valido as obter_token_fit, salvar_tokens as salvar_tokens_fit, obter_passos_diarios, obter_batimentos_medios, obter_sono, obter_ultimo_peso, obter_ultima_altura
from utils.dados_alimentos import buscar_info_alimento, gerar_dicas_nutricionais

# --- Configuração OAuth ---
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

client_config_google = {"web": {"client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET, "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": GOOGLE_TOKEN_URI, "redirect_uris": [GOOGLE_REDIRECT_URI]}}
STRAVA_AUTH_URL = f"https://www.strava.com/oauth/authorize?client_id={STRAVA_CLIENT_ID}&response_type=code&redirect_uri={STRAVA_REDIRECT_URI}&approval_prompt=force&scope=read_all,activity:read_all"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"

# --- DB Local ---
def init_db():
    conn = sqlite3.connect("health_data.db")
    conn.execute('''CREATE TABLE IF NOT EXISTS health_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        peso_kg REAL,
        altura_m REAL,
        imc REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

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
    except:
        return pd.DataFrame()

def classificar_imc(imc):
    if imc < 18.5: return "Abaixo do peso"
    elif imc < 25: return "Peso normal"
    elif imc < 30: return "Sobrepeso"
    elif imc < 35: return "Obesidade grau I"
    elif imc < 40: return "Obesidade grau II"
    else: return "Obesidade grau III"

# --- Página Principal ---
st.set_page_config(page_title="Painel de Saúde", layout="wide")
st.sidebar.title("🔗 Conexões")

# --- Autenticação ---
query_params = st.query_params
code = query_params.get("code")
scope = query_params.get("scope")

if code and "auth_flow" not in st.session_state:
    st.session_state.auth_flow = True
    if scope and "activity:read_all" in scope:
        r = requests.post(STRAVA_TOKEN_URL, data={"client_id": STRAVA_CLIENT_ID, "client_secret": STRAVA_CLIENT_SECRET, "code": code, "grant_type": "authorization_code"})
        if r.ok:
            salvar_tokens_strava(r.json(), STRAVA_TOKEN_FILE)
            st.success("Strava conectado!")
            time.sleep(1)
            st.query_params.clear()
    elif scope:
        flow = Flow.from_client_config(client_config_google, scopes=GOOGLE_SCOPES, redirect_uri=GOOGLE_REDIRECT_URI)
        flow.fetch_token(code=code)
        cred = flow.credentials
        tokens = {
            'access_token': cred.token,
            'refresh_token': cred.refresh_token,
            'token_uri': cred.token_uri,
            'client_id': cred.client_id,
            'client_secret': cred.client_secret,
            'scopes': cred.scopes,
            'expires_at': cred.expiry.timestamp() if cred.expiry else None
        }
        salvar_tokens_fit(tokens, GOOGLE_TOKEN_FILE)
        st.success("Google Fit conectado!")
        time.sleep(1)
        st.query_params.clear()

# --- Sidebar tokens ---
token_strava = obter_token_strava(STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_TOKEN_FILE)
if token_strava:
    st.sidebar.success("✅ Strava Conectado")
else:
    st.sidebar.markdown(f"[Conectar Strava]({STRAVA_AUTH_URL})")

token_google = obter_token_fit(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_TOKEN_URI, GOOGLE_TOKEN_FILE)
if token_google:
    st.sidebar.success("✅ Google Fit Conectado")
else:
    flow = Flow.from_client_config(client_config_google, scopes=GOOGLE_SCOPES, redirect_uri=GOOGLE_REDIRECT_URI)
    auth_url, _ = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    st.sidebar.markdown(f"[Conectar Google Fit]({auth_url})")

# --- Tabs ---
st.title("🏥 Painel Integrado de Saúde")
tabs = st.tabs(["🧮 IMC", "🧍 Google Fit", "🚴 Strava", "🥗 Alimentos"])

with tabs[0]:
    st.header("🧮 IMC e Histórico")
    peso = st.number_input("Peso (kg)", 40.0, 300.0, step=0.1)
    altura = st.number_input("Altura (m)", 1.0, 2.5, step=0.01)
    if st.button("Calcular IMC"):
        if altura > 0:
            imc = round(peso / (altura ** 2), 2)
            salvar_dado(peso, altura, imc)
            st.success(f"IMC: {imc} ({classificar_imc(imc)})")

    df = buscar_dados_locais()
    if not df.empty:
        st.plotly_chart(px.line(df, x="timestamp", y="imc", title="Evolução do IMC"))
        st.dataframe(df)

with tabs[1]:
    st.header("🧍 Dados do Google Fit")
    if token_google:
        hoje = datetime.now().date()
        inicio = datetime.combine(hoje - timedelta(days=6), datetime.min.time())
        fim = datetime.combine(hoje, datetime.max.time())

        passos = obter_passos_diarios(token_google)
        batimentos = obter_batimentos_medios(token_google, inicio, fim)
        sono = obter_sono(token_google)
        peso = obter_ultimo_peso(token_google)
        altura = obter_ultima_altura(token_google)

        st.metric("Passos hoje", f"{passos.get(str(hoje), 0):,}")
        st.metric("Peso (Google Fit)", f"{peso:.1f} kg")
        st.metric("Altura (Google Fit)", f"{altura:.2f} m")
        st.plotly_chart(px.bar(pd.DataFrame(list(passos.items()), columns=["Data", "Passos"]), x="Data", y="Passos"))
        st.plotly_chart(px.line(pd.DataFrame(batimentos), x="Data", y="Batimentos"))
        st.plotly_chart(px.bar(pd.DataFrame(sono), x="Data", y="Horas de Sono"))
    else:
        st.warning("Google Fit não conectado.")

with tabs[2]:
    st.header("🚴 Atividades Strava")
    if token_strava:
        atividades, atleta_id = buscar_ultimas_atividades(token_strava)
        stats = buscar_estatisticas_atleta(token_strava, atleta_id)
        if stats:
            st.metric("Distância Corrida", f"{stats['corrida_distancia_km']} km")
            st.metric("Distância Pedalada", f"{stats['pedalada_distancia_km']} km")
        if atividades:
            nomes = [a['nome'] for a in atividades]
            sel = st.selectbox("Atividade", nomes)
            for a in atividades:
                if a['nome'] == sel:
                    st.write(f"Distância: {a['distancia_km']} km — Tempo: {a['duracao_min']} min")
                    if a['mapa']:
                        html = gerar_mapa_atividade(a)
                        st.components.v1.html(html, height=500)
    else:
        st.warning("Strava não conectado.")

with tabs[3]:
    st.header("🥗 Consulta de Alimentos")
    nome = st.text_input("Nome do alimento")
    if st.button("Buscar"):
        dados = buscar_info_alimento(nome)
        if dados:
            st.image(dados["imagem"], width=150)
            st.write(f"**Nome:** {dados['nome']}")
            st.write(f"**Nutri-Score:** {dados['nutriscore'].upper()}")
            st.write(f"**Grupo NOVA:** {dados['nova_group']}")
            st.write("---")
            st.write(f"**Calorias:** {dados['calorias']} kcal")
            st.write(f"**Proteínas:** {dados['proteinas']} g")
            st.write(f"**Gordura Saturada:** {dados['gordura_saturada']} g")
            st.write(f"**Açúcar:** {dados['açucar']} g")
            st.write("---")
            dicas = gerar_dicas_nutricionais(dados)
            for dica in dicas:
                st.markdown(dica)
        else:
            st.warning("Alimento não encontrado")
