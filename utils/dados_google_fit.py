# utils/dados_google_fit.py
import json
import os
import requests
import time
from datetime import datetime, timedelta

def salvar_tokens(tokens, token_file):
    with open(token_file, "w") as f:
        json.dump(tokens, f, indent=4)
    print("✅ Tokens do Google Fit salvos.")

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
    print("🔄 Atualizando token do Google Fit...")
    response = requests.post(token_uri, data={
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'refresh_token': tokens['refresh_token']
    })
    if response.status_code == 200:
        novos_tokens = response.json()
        tokens.update({
            'access_token': novos_tokens.get('access_token'),
            'expires_at': time.time() + novos_tokens.get('expires_in', 3600)
        })
        salvar_tokens(tokens, token_file)
        return tokens
    else:
        print(f"❌ Erro ao atualizar token Google: {response.text}")
        return None

def obter_token_valido(client_id, client_secret, token_uri, token_file):
    tokens = carregar_tokens(token_file)
    if not tokens: return None
    if token_expirado(tokens): return atualizar_token(client_id, client_secret, token_uri, token_file)
    return tokens

def fazer_requisicao(token, data_source_id, start_time, end_time):
    url = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "aggregateBy": [{"dataSourceId": data_source_id}],
        "bucketByTime": {"durationMillis": 86400000},
        "startTimeMillis": int(start_time.timestamp() * 1000),
        "endTimeMillis": int(end_time.timestamp() * 1000)
    }
    try:
        r = requests.post(url, headers=headers, json=body)
        r.raise_for_status()
        return r.json().get("bucket", [])
    except requests.RequestException as e:
        print(f"Erro na requisição ao Google Fit: {e}")
        return []

def obter_passos_diarios(token):
    # ... (cole sua função obter_passos_diarios aqui) ...
    return []

def obter_batimentos_medios(token):
    # ... (cole sua função obter_batimentos_medios aqui) ...
    return []

def obter_sono(token):
    # ... (cole sua função obter_sono aqui) ...
    return []

# --- NOVAS FUNÇÕES ADICIONADAS ---
def obter_ultimo_peso(token):
    """Busca a medição de peso mais recente dos últimos 30 dias."""
    end = datetime.now()
    start = end - timedelta(days=30)
    data_source_id = "derived:com.google.weight:com.google.android.gms:merge_weight"
    url = "https://www.googleapis.com/fitness/v1/users/me/dataSources/" + data_source_id + "/datasets"
    dataset_id = f"{int(start.timestamp() * 1e9)}-{int(end.timestamp() * 1e9)}"
    full_url = f"{url}/{dataset_id}"
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    try:
        r = requests.get(full_url, headers=headers)
        r.raise_for_status()
        data = r.json()
        if 'point' in data and data['point']:
            ultimo_ponto = data['point'][-1]
            peso = ultimo_ponto['value'][0]['fpVal']
            return round(peso, 1)
    except requests.RequestException as e:
        print(f"Erro ao buscar peso do Google Fit: {e}")
    return None

def obter_ultima_altura(token):
    """Busca a medição de altura mais recente dos últimos 365 dias."""
    end = datetime.now()
    start = end - timedelta(days=365)
    data_source_id = "derived:com.google.height:com.google.android.gms:merge_height"
    url = "https://www.googleapis.com/fitness/v1/users/me/dataSources/" + data_source_id + "/datasets"
    dataset_id = f"{int(start.timestamp() * 1e9)}-{int(end.timestamp() * 1e9)}"
    full_url = f"{url}/{dataset_id}"
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    try:
        r = requests.get(full_url, headers=headers)
        r.raise_for_status()
        data = r.json()
        if 'point' in data and data['point']:
            ultimo_ponto = data['point'][-1]
            altura = ultimo_ponto['value'][0]['fpVal']
            return round(altura, 2)
    except requests.RequestException as e:
        print(f"Erro ao buscar altura do Google Fit: {e}")
    return None