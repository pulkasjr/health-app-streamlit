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
    if token_expirado(tokens):
        return atualizar_token(client_id, client_secret, token_uri, token_file)
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
    end = datetime.now()
    start = end - timedelta(days=7)
    data_source_id = "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps"
    buckets = fazer_requisicao(token['access_token'], data_source_id, start, end)
    resultados = []
    for b in buckets:
        data = datetime.fromtimestamp(int(b["startTimeMillis"]) / 1000).strftime("%d/%m")
        pontos = b.get("dataset", [{}])[0].get("point", [])
        passos = sum(int(dp["value"][0]["intVal"]) for dp in pontos if dp.get("value"))
        if passos > 0:
            resultados.append({"data": data, "passos": passos})
    return resultados

def obter_batimentos_medios(token):
    end = datetime.now()
    start = end - timedelta(days=7)
    data_source_id = "derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm"
    buckets = fazer_requisicao(token['access_token'], data_source_id, start, end)
    resultados = []
    for b in buckets:
        data = datetime.fromtimestamp(int(b["startTimeMillis"]) / 1000).strftime("%d/%m")
        pontos = b.get("dataset", [{}])[0].get("point", [])
        bpm_list = [p["value"][0]["fpVal"] for p in pontos if p.get("value")]
        if bpm_list:
            media = round(sum(bpm_list) / len(bpm_list), 1)
            resultados.append({"data": data, "bpm": media})
    return resultados

def obter_sono(token):
    end = datetime.now()
    start = end - timedelta(days=7)
    data_source_id = "derived:com.google.sleep.segment:com.google.android.gms:merged"
    buckets = fazer_requisicao(token['access_token'], data_source_id, start, end)
    resultados = []
    for b in buckets:
        data_sono = (datetime.fromtimestamp(int(b["startTimeMillis"]) / 1000) - timedelta(hours=12)).strftime("%d/%m")
        pontos = b.get("dataset", [{}])[0].get("point", [])
        total_nanos = sum(int(p["endTimeNanos"]) - int(p["startTimeNanos"]) for p in pontos if p.get("value") and p["value"][0]["intVal"] not in [1, 3])
        duracao_horas = round(total_nanos / 3.6e12, 2)
        if duracao_horas > 0:
            resultados.append({"data": data_sono, "duracao_horas": duracao_horas})
    return resultados