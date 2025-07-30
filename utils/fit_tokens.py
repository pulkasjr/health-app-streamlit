# utils/fit_tokens.py
import json
import os
import requests
import time

def salvar_tokens(tokens, token_file):
    with open(token_file, "w") as f:
        json.dump(tokens, f, indent=4)
    print("✅ Tokens do Google Fit salvos com sucesso.")

def carregar_tokens(token_file):
    if not os.path.exists(token_file): return None
    try:
        with open(token_file, "r") as f: return json.load(f)
    except json.JSONDecodeError: return None

def token_expirado(tokens):
    if not tokens or "expires_at" not in tokens: return True
    return time.time() >= tokens["expires_at"]

def atualizar_token(client_id, client_secret, token_uri, token_file):
    tokens = carregar_tokens(token_file)
    if not tokens or "refresh_token" not in tokens: return None

    print("🔄 Atualizando token de acesso do Google Fit...")
    response = requests.post(token_uri, data={
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'refresh_token': tokens['refresh_token']
    })

    if response.status_code == 200:
        novos_tokens = response.json()
        tokens.update({
            'access_token': novos_tokens['access_token'],
            'expires_at': time.time() + novos_tokens['expires_in']
        })
        salvar_tokens(tokens, token_file)
        return tokens
    else:
        print(f"❌ Erro ao atualizar token do Google: {response.text}")
        return None

def obter_token_valido(client_id, client_secret, token_uri, token_file):
    tokens = carregar_tokens(token_file)
    if not tokens: return None
    if token_expirado(tokens):
        return atualizar_token(client_id, client_secret, token_uri, token_file)
    return tokens