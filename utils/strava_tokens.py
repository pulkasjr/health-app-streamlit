# utils/strava_tokens.py
import json
import os
import requests
from datetime import datetime

def salvar_tokens(tokens, token_file):
    with open(token_file, "w") as f:
        json.dump(tokens, f, indent=4)
    print("✅ Tokens do Strava salvos com sucesso.")

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

    print("🔄 Atualizando token de acesso do Strava...")
    response = requests.post("https://www.strava.com/oauth/token", data={
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
        print(f"❌ Erro ao atualizar token do Strava: {response.text}")
        return None

def obter_token_valido(client_id, client_secret, token_file):
    tokens = carregar_tokens(token_file)
    if not tokens: return None
    if token_expirado(tokens):
        return atualizar_token(client_id, client_secret, token_file)
    return tokens