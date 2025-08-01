# utils/dados_strava.py
import json
import os
import requests
from datetime import datetime
import polyline
import folium

STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_API_URL = "https://www.strava.com/api/v3/athlete/activities"

def salvar_tokens(tokens, token_file):
    with open(token_file, "w") as f:
        json.dump(tokens, f, indent=4)
    print("✅ Tokens do Strava salvos.")

def carregar_tokens(token_file):
    if not os.path.exists(token_file): return None
    try:
        with open(token_file, "r") as f: return json.load(f)
    except json.JSONDecodeError: return None

def token_expirado(tokens):
    return int(tokens.get("expires_at", 0)) < int(datetime.utcnow().timestamp())

def atualizar_token(client_id, client_secret, token_file):
    tokens = carregar_tokens(token_file)
    if not tokens or "refresh_token" not in tokens: return None
    print("🔄 Atualizando token do Strava...")
    response = requests.post(STRAVA_TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"]
    })
    if response.status_code == 200:
        novos_tokens = response.json()
        salvar_tokens(novos_tokens, token_file)
        return novos_tokens
    else:
        print(f"❌ Erro ao atualizar token Strava: {response.text}")
        return None

def obter_token_valido(client_id, client_secret, token_file):
    tokens = carregar_tokens(token_file)
    if not tokens: return None
    if token_expirado(tokens): return atualizar_token(client_id, client_secret, token_file)
    return tokens

def buscar_ultimas_atividades(token, quantidade=5):
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    try:
        r = requests.get(STRAVA_API_URL, headers=headers, params={"per_page": quantidade})
        r.raise_for_status()
        atividades = []
        for atividade in r.json():
            atividades.append({
                "id": atividade["id"],
                "nome": atividade["name"],
                "distancia_km": round(atividade.get("distance", 0) / 1000, 2),
                "duracao_min": round(atividade.get("moving_time", 0) / 60),
                "mapa": atividade.get("map", {}).get("summary_polyline")
            })
        return atividades
    except requests.RequestException as e:
        print(f"Erro ao buscar atividades do Strava: {e}")
        return []

def gerar_mapa_atividade(atividade):
    poly = atividade.get("mapa")
    if not poly: return "<p>Sem dados de rota.</p>"
    try:
        coords = polyline.decode(poly)
        if not coords: return "<p>Sem dados de rota.</p>"
        mapa = folium.Map(location=coords[0], zoom_start=13)
        folium.PolyLine(coords, color="#fc4c02", weight=3.5, opacity=1).add_to(mapa)
        folium.Marker(location=coords[0], popup="Início", icon=folium.Icon(color="green")).add_to(mapa)
        folium.Marker(location=coords[-1], popup="Fim", icon=folium.Icon(color="red")).add_to(mapa)
        return mapa._repr_html_()
    except Exception as e:
        print(f"Erro ao gerar mapa: {e}")
        return "<p>Erro ao gerar mapa.</p>"