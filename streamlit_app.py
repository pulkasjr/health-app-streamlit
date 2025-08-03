# CÓDIGO FINAL, COMPLETO E COM OS ESCOPOS CORRETOS

import streamlit as st
import os
import json
import requests
from datetime import datetime
import time

# Importações da biblioteca do Google
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# --- Importações dos seus módulos de utilidades ---
from utils.dados_google_fit import obter_passos_diarios, obter_batimentos_medios, obter_sono, obter_ultimo_peso, obter_ultima_altura
from utils.dados_strava import buscar_ultimas_atividades, buscar_estatisticas_atleta, gerar_mapa_atividade
from utils.dados_alimentos import buscar_info_alimento, gerar_dicas_nutricionais

# --- Configurações e Constantes ---
st.set_page_config(page_title="Painel de Saúde", layout="wide")

# --- Credenciais ---
STRAVA_CLIENT_ID = "168833" # SUBSTITUA AQUI
STRAVA_CLIENT_SECRET = "6e774fa2c3c62214ea196fbcdf8162a00e58a882" # SUBSTITUA AQUI
STRAVA_TOKEN_FILE = "strava_tokens.json"
GOOGLE_CLIENT_SECRETS_FILE = "client_secret.json" 
GOOGLE_TOKEN_FILE = "google_fit_tokens.json"

# ESTA É A LISTA DE ESCOPOS COMPLETA E CORRETA
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/fitness.activity.read',
    'https://www.googleapis.com/auth/fitness.body.read',
    'https://www.googleapis.com/auth/fitness.heart_rate.read',
    'https://www.googleapis.com/auth/fitness.sleep.read'
]

REDIRECT_URI = "http://localhost:8501"

# ==============================================================================
# FUNÇÕES DE AUTENTICAÇÃO
# ==============================================================================

def gerenciar_autenticacao_strava_ui():
    auth_code, auth_state = st.query_params.get("code"), st.query_params.get("state")
    if auth_code and auth_state == "strava":
        with st.spinner("Conectando ao Strava..."):
            response = requests.post("https://www.strava.com/oauth/token", data={"client_id": STRAVA_CLIENT_ID, "client_secret": STRAVA_CLIENT_SECRET, "code": auth_code, "grant_type": "authorization_code"})
            if response.status_code == 200:
                with open(STRAVA_TOKEN_FILE, 'w') as f: json.dump(response.json(), f)
                st.query_params.clear(); st.success("Strava conectado!"); time.sleep(1); st.rerun()
            else: st.error(f"Falha na autenticação: {response.text}")
    else:
        auth_url = f"https://www.strava.com/oauth/authorize?client_id={STRAVA_CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&approval_prompt=force&scope=read,activity:read_all,profile:read_all&state=strava"
        st.link_button("🔗 Conectar ao Strava", auth_url, use_container_width=True)

def gerenciar_autenticacao_google_ui():
    if not os.path.exists(GOOGLE_CLIENT_SECRETS_FILE):
        st.error(f"Arquivo de credenciais '{GOOGLE_CLIENT_SECRETS_FILE}' não encontrado."); return
    flow = Flow.from_client_secrets_file(GOOGLE_CLIENT_SECRETS_FILE, scopes=GOOGLE_SCOPES, redirect_uri=REDIRECT_URI)
    auth_code, auth_state = st.query_params.get("code"), st.query_params.get("state")
    if auth_code and auth_state == "google":
        with st.spinner("Conectando ao Google Fit..."):
            flow.fetch_token(code=auth_code)
            with open(GOOGLE_TOKEN_FILE, 'w') as token: token.write(flow.credentials.to_json())
            st.query_params.clear(); st.success("Google Fit conectado!"); time.sleep(1); st.rerun()
    else:
        authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true', prompt='consent', state='google')
        st.link_button("🔗 Conectar ao Google Fit", authorization_url, use_container_width=True)

# ==============================================================================
# LAYOUT PRINCIPAL
# ==============================================================================

st.title("📊 Painel de Saúde Integrado")
tab_conexoes, tab_fit, tab_strava, tab_alimentos = st.tabs(["🚪 Conexões", "📱 Google Fit", "🏃 Strava", "🍎 Alimentos"])

with tab_conexoes:
    st.header("Gerencie suas Conexões")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Google Fit")
        if os.path.exists(GOOGLE_TOKEN_FILE):
            st.success("✅ Conectado ao Google Fit.")
            if st.button("Desconectar Google"): os.remove(GOOGLE_TOKEN_FILE); st.rerun()
        else: gerenciar_autenticacao_google_ui()
    with col2:
        st.subheader("Strava")
        if os.path.exists(STRAVA_TOKEN_FILE):
            st.success("✅ Conectado ao Strava.")
            if st.button("Desconectar Strava"): os.remove(STRAVA_TOKEN_FILE); st.rerun()
        else: gerenciar_autenticacao_strava_ui()

with tab_fit:
    st.header("Seus dados do Google Fit")
    if os.path.exists(GOOGLE_TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_FILE, GOOGLE_SCOPES)
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            
            with st.spinner("Buscando dados do Google Fit..."):
                peso = obter_ultimo_peso(creds)
                altura = obter_ultima_altura(creds)
                passos = obter_passos_diarios(creds)
                bpm = obter_batimentos_medios(creds)
                sono = obter_sono(creds)
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("⚖️ IMC")
                if peso and altura:
                    imc = round(peso / (altura ** 2), 1)
                    st.metric("Seu IMC Atual", f"{imc}")
                else: st.warning("Adicione peso/altura no app Google Fit.")
            with col2:
                st.subheader("❤️ Batimentos Médios")
                if bpm: st.line_chart(bpm)
                else: st.info("Nenhum dado de batimentos encontrado.")

            st.subheader("📶 Passos Diários")
            if passos: st.bar_chart(passos)
            else: st.info("Nenhum dado de passos encontrado.")
            
            st.subheader("😴 Horas de Sono")
            if sono: st.area_chart(sono)
            else: st.info("Nenhum dado de sono encontrado.")

        except Exception as e:
            st.error(f"Ocorreu um erro ao carregar os dados do Google: {e}")
            st.warning("Tente desconectar e conectar novamente na aba 'Conexões'.")
    else:
        st.info("⬅️ Conecte sua conta na aba 'Conexões'.")

with tab_strava:
    st.header("Suas Atividades do Strava")
    if os.path.exists(STRAVA_TOKEN_FILE):
        with open(STRAVA_TOKEN_FILE, 'r') as f: tokens = json.load(f)
        access_token = tokens['access_token']
        if tokens['expires_at'] < time.time():
            st.warning("Token do Strava expirado. Por favor, vá para a aba 'Conexões' e reconecte.")
        else:
            with st.spinner("Buscando dados do Strava..."):
                atividades, atleta_id = buscar_ultimas_atividades(access_token)
            
            if atleta_id:
                stats = buscar_estatisticas_atleta(access_token, atleta_id)
                if stats:
                    c1, c2 = st.columns(2)
                    c1.metric("Total Corrida (Ano)", f"{stats['corrida_distancia_km']} km")
                    c2.metric("Total Pedalada (Ano)", f"{stats['pedalada_distancia_km']} km")
            
            if atividades:
                st.subheader("Suas Últimas Atividades")
                for at in atividades:
                    with st.expander(f"**{at['nome']}** ({at['tipo']}) - {at['distancia_km']} km"):
                        st.write(f"**Distância:** {at['distancia_km']} km | **Duração:** {at['duracao_min']} min")
                        mapa_html = gerar_mapa_atividade(at)
                        st.components.v1.html(mapa_html, height=350, scrolling=False)
            else: st.info("Nenhuma atividade recente encontrada.")
    else:
        st.info("⬅️ Conecte sua conta na aba 'Conexões'.")

with tab_alimentos:
    st.header("🍎 Consulta de Alimentos")
    alimento = st.text_input("Digite um alimento para consultar:", key="food_input")
    if alimento:
        with st.spinner(f"Buscando informações sobre '{alimento}'..."):
            dados = buscar_info_alimento(alimento)
        if dados:
            st.subheader(dados.get('nome', 'Nome não disponível'))
            if dados.get("imagem"): st.image(dados.get("imagem"), width=200)
            st.write(f"**Nutri-Score:** {dados.get('nutriscore', '?').upper()} | **Grupo NOVA:** {dados.get('nova_group', '?')}")
            st.write(f"**Ingredientes:** {dados.get('ingredientes', 'Não listado')}")
            
            st.subheader("💡 Dicas Nutricionais")
            dicas = gerar_dicas_nutricionais(dados)
            for dica in dicas: st.markdown(f"- {dica}")
        else:
            st.error("❌ Alimento não encontrado.")
    else:
        st.info("Digite o nome de um alimento acima para ver suas informações nutricionais.")