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

# Importando as funções dos módulos utils
from utils.dados_strava import obter_token_valido as obter_token_strava, salvar_tokens as salvar_tokens_strava, buscar_ultimas_atividades, gerar_mapa_atividade
from utils.dados_google_fit import obter_token_valido as obter_token_fit, salvar_tokens as salvar_tokens_fit, obter_passos_diarios, obter_batimentos_medios, obter_sono, obter_ultimo_peso, obter_ultima_altura
from utils.dados_alimentos import buscar_info_alimento, gerar_dicas_nutricionais

# ----- CONFIGURAÇÃO CENTRALIZADA (COLOQUE SUAS CREDENCIAIS CORRETAS AQUI) -----
STRAVA_CLIENT_ID = "168833"
STRAVA_CLIENT_SECRET = "6e774fa2c3c62214ea196fbcdf8162a00e58a882"
SSTRAVA_REDIRECT_URI = "https://health-app-streamlit.onrender.com"
STRAVA_TOKEN_FILE = "strava_tokens.json"

GOOGLE_CLIENT_ID = "423426384359-m0pr10393ve0seul953bh63lhobqgl2v.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"
GOOGLE_REDIRECT_URI = "https://health-app-streamlit.onrender.com"
GOOGLE_TOKEN_FILE = "google_fit_tokens.json"
GOOGLE_TOKEN_URI = 'https://oauth2.googleapis.com/token'
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/fitness.activity.read", 
    "https://www.googleapis.com/auth/fitness.body.read",
    "https://www.googleapis.com/auth/fitness.heart_rate.read",
    "https://www.googleapis.com/auth/fitness.sleep.read"
]

# --- Construção dos objetos de configuração ---
client_config_google = {"web": {"client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET, "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": GOOGLE_TOKEN_URI, "redirect_uris": [GOOGLE_REDIRECT_URI]}}
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
    conn = sqlite3.connect("health_data.db")
    df = pd.read_sql_query("SELECT * FROM health_records ORDER BY timestamp DESC", conn, parse_dates=["timestamp"])
    conn.close()
    return df

def classificar_imc(imc):
    if imc < 18.5: return ("Abaixo do Peso", "imc-abaixo")
    elif 18.5 <= imc < 25: return ("Peso Normal", "imc-normal")
    elif 25 <= imc < 30: return ("Sobrepeso", "imc-sobrepeso")
    elif 30 <= imc < 35: return ("Obesidade Grau I", "imc-obesidade-1")
    elif 35 <= imc < 40: return ("Obesidade Grau II", "imc-obesidade-2")
    else: return ("Obesidade Grau III", "imc-obesidade-3")

# ----- LÓGICA DO STREAMLIT -----
st.set_page_config(page_title="Painel de Saúde", layout="wide")

# Injeta CSS para colorir as classificações de IMC
st.markdown("""
<style>
.imc-abaixo { color: #007bff; font-weight: bold; } .imc-normal { color: #28a745; font-weight: bold; }
.imc-sobrepeso { color: #fd7e14; font-weight: bold; } .imc-obesidade-1 { color: #dc3545; font-weight: bold; }
.imc-obesidade-2 { color: #c82333; font-weight: bold; } .imc-obesidade-3 { color: #a71d2a; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

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
                time.sleep(1); st.query_params.clear()
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
                time.sleep(1); st.query_params.clear()
        except Exception as e:
            st.error(f"Erro na autorização do Google: {e}")

# --- BARRA LATERAL (SIDEBAR) ---
st.sidebar.title("VidaCheck Saúde")

token_strava = obter_token_strava(STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_TOKEN_FILE)
if token_strava:
    st.sidebar.success("✅ Conectado ao Strava")
else:
    st.sidebar.warning("🔴 Não conectado ao Strava")
    st.sidebar.markdown(f'<a href="{STRAVA_AUTH_URL}" target="_self">Conectar com Strava</a>', unsafe_allow_html=True)

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

# --- LÓGICA DE PRÉ-PREENCHIMENTO ---
peso_fit, altura_fit = None, None
if token_google:
    with st.spinner("Buscando dados de peso e altura..."):
        peso_fit = obter_ultimo_peso(token_google)
        altura_fit = obter_ultima_altura(token_google)

# --- Abas ---
tabs = st.tabs(["🧮 IMC & Glicemia", "🧍 Google Fit", "🚴 Strava", "🥗 Alimentos"])

# --- Aba IMC & Glicemia ---
with tabs[0]:
    st.header("🧮 Meu Histórico Manual")
    with st.expander("➕ Adicionar Novo Registro de Peso e Altura"):
        with st.form("formulario_imc", clear_on_submit=True):
            peso_inicial = peso_fit if peso_fit else 70.0
            altura_inicial = altura_fit if altura_fit else 1.70
            peso = st.number_input("Peso (kg)", min_value=20.0, max_value=300.0, step=0.1, value=peso_inicial, format="%.1f")
            altura = st.number_input("Altura (m)", min_value=1.0, max_value=2.5, step=0.01, value=altura_inicial, format="%.2f")
            enviado = st.form_submit_button("Salvar e Calcular IMC")
            if enviado and altura > 0:
                imc = round(peso / (altura ** 2), 2)
                salvar_dado(peso, altura, imc)
                classificacao_texto, _ = classificar_imc(imc)
                st.success(f"IMC: {imc} ({classificacao_texto}) — salvo!")
            elif enviado:
                st.error("A altura deve ser maior que zero.")
    
    df_local = buscar_dados_locais()
    if not df_local.empty:
        st.subheader("📜 Histórico e Evolução do IMC")
        df_local[['classificacao_texto', 'classificacao_css']] = df_local['imc'].apply(lambda imc: pd.Series(classificar_imc(imc)))
        def formatar_classificacao(row):
            return f'<span class="{row["classificacao_css"]}">{row["classificacao_texto"]}</span>'
        df_local['Classificação'] = df_local.apply(formatar_classificacao, axis=1)
        df_para_exibir = df_local[['timestamp', 'peso_kg', 'altura_m', 'imc', 'Classificação']].rename(columns={'timestamp':'Data', 'peso_kg':'Peso (kg)', 'altura_m':'Altura (m)', 'imc':'IMC'})
        st.write(df_para_exibir.to_html(escape=False, index=False), unsafe_allow_html=True)
        fig = px.line(df_local.sort_values("timestamp"), x="timestamp", y="imc", title="Evolução do IMC", markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhum dado de IMC armazenado ainda.")

    st.markdown("---") 
    st.header("🩸 Glicemia (Importar do mySugr)")
    st.info("Exporte seu relatório em formato CSV no app mySugr e faça o upload aqui.")
    uploaded_file = st.file_uploader("Escolha o seu arquivo CSV do mySugr", type="csv")
    if uploaded_file is not None:
        try:
            coluna_data = "Data"
            coluna_glicemia = "Glicemia" # Ajuste o nome exato da coluna do seu arquivo
            df_glicemia = pd.read_csv(uploaded_file, sep=';', decimal=',')
            st.success("Arquivo carregado com sucesso!")
            df_glicemia = df_glicemia.rename(columns={coluna_data: 'timestamp', coluna_glicemia: 'glicemia'})
            df_glicemia = df_glicemia[['timestamp', 'glicemia']].dropna()
            df_glicemia['timestamp'] = pd.to_datetime(df_glicemia['timestamp'], dayfirst=True)
            df_glicemia['glicemia'] = pd.to_numeric(df_glicemia['glicemia'])
            st.subheader("Visão Geral dos Dados de Glicemia Importados")
            st.dataframe(df_glicemia)
            st.subheader("Evolução da Glicemia")
            fig_glicemia = px.line(df_glicemia.sort_values("timestamp"), x="timestamp", y="glicemia", title="Histórico de Glicemia (do arquivo CSV)", markers=True)
            st.plotly_chart(fig_glicemia, use_container_width=True)
        except Exception as e:
            st.error(f"Ocorreu um erro ao processar o arquivo: {e}")

# --- Aba Google Fit ---
with tabs[1]:
    st.header("🧍 Dados do Google Fit (Últimos 7 dias)")
    if token_google:
        with st.spinner("Buscando dados do Google Fit..."):
            passos = obter_passos_diarios(token_google)
            bpm = obter_batimentos_medios(token_google)
            sono = obter_sono(token_google)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            passos_hoje = passos[-1]['passos'] if passos else 0
            st.metric(label="👣 Passos Hoje", value=f"{passos_hoje}")
        with col2:
            bpm_ontem = bpm[-1]['bpm'] if bpm else 0
            st.metric(label="❤️ Batimentos (Média Ontem)", value=f"{bpm_ontem:.0f} bpm" if bpm else "N/A")
        with col3:
            sono_ontem = sono[-1]['duracao_horas'] if sono else 0
            st.metric(label="😴 Sono (Última Noite)", value=f"{sono_ontem:.1f} horas" if sono else "N/A")
        
        st.markdown("---")
        if passos:
            st.subheader("📈 Evolução dos Passos")
            df_passos = pd.DataFrame(passos)
            fig_passos = px.bar(df_passos, x="data", y="passos", title="Passos Diários")
            st.plotly_chart(fig_passos, use_container_width=True)
        if bpm:
            st.subheader("📈 Evolução dos Batimentos")
            df_bpm = pd.DataFrame(bpm)
            fig_bpm = px.line(df_bpm, x="data", y="bpm", title="Batimentos por Dia", markers=True)
            st.plotly_chart(fig_bpm, use_container_width=True)
        if sono:
            st.subheader("📈 Evolução do Sono")
            df_sono = pd.DataFrame(sono)
            fig_sono = px.bar(df_sono, x="data", y="duracao_horas", title="Horas de Sono por Noite")
            st.plotly_chart(fig_sono, use_container_width=True)
    else:
        st.warning("Conecte sua conta do Google Fit na barra lateral para ver os dados automáticos.")

# --- Aba Strava ---
with tabs[2]:
    st.header("🚴 Atividades do Strava")
    if token_strava:
        with st.spinner("Buscando atividades do Strava..."):
            atividades = buscar_ultimas_atividades(token_strava)
        if atividades:
            st.subheader("🏃 Últimas 5 Atividades")
            nomes_atividades = [a['nome'] for a in atividades]
            atividade_selecionada = st.selectbox("Selecione uma atividade para ver os detalhes:", nomes_atividades)
            for a in atividades:
                if a['nome'] == atividade_selecionada:
                    st.markdown(f"**Distância:** {a['distancia_km']} km | **Duração:** {a['duracao_min']} min")
                    if a.get("mapa"):
                        st.subheader(f"📍 Mapa de '{a['nome']}'")
                        mapa_html = gerar_mapa_atividade(a)
                        st.components.v1.html(mapa_html, height=500, scrolling=True)
                    else:
                        st.info("Esta atividade não possui um mapa.")
                    break
        else:
            st.info("Nenhuma atividade recente encontrada no Strava.")
    else:
        st.warning("Conecte sua conta do Strava na barra lateral para ver suas atividades.")

# --- Aba Alimentos ---
with tabs[3]:
    st.header("🥗 Consulta de Alimentos (Open Food Facts)")
    alimento = st.text_input("Digite o nome de um alimento para buscar:")
    if st.button("Buscar Alimento"):
        if alimento:
            with st.spinner("Buscando informações nutricionais..."):
                dados = buscar_info_alimento(alimento)
            if dados:
                st.markdown(f"### 🥣 {dados['nome']}")
                col1, col2 = st.columns([1, 2])
                with col1:
                    if dados["imagem"]: st.image(dados["imagem"], width=150)
                    st.write(f"**Nutri-Score:** {dados['nutriscore'].upper()}")
                with col2:
                    st.write(f"**Calorias (100g):** {dados.get('calorias', 0)} kcal")
                    st.write(f"**Açúcar (100g):** {dados.get('açucar', 0)} g")
                    st.write(f"**Gordura (100g):** {dados.get('gordura', 0)} g")
                    st.write(f"**Sal (100g):** {dados.get('sal', 0)} g")
                
                st.markdown("---")
                st.markdown("### 💡 Recomendações Nutricionais")
                dicas = gerar_dicas_nutricionais(dados)
                for dica in dicas: st.write(dica)
            else:
                st.warning("Alimento não encontrado. Tente outro nome.")
        else:
            st.warning("Por favor, digite o nome de um alimento.")