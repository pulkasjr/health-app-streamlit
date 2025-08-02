import requests
from datetime import datetime

# Passos Diários

def obter_passos_diarios(token, inicio, fim):
    url = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "aggregateBy": [{"dataTypeName": "com.google.step_count.delta"}],
        "bucketByTime": {"durationMillis": 86400000},
        "startTimeMillis": int(inicio.strftime("%s")) * 1000,
        "endTimeMillis": int(fim.strftime("%s")) * 1000
    }
    try:
        response = requests.post(url, headers=headers, json=body)
        data = response.json()
        resultados = {}
        for bucket in data.get("bucket", []):
            data_inicio = datetime.fromtimestamp(int(bucket["startTimeMillis"]) / 1000).date()
            total = sum(v.get("intVal", 0) for d in bucket.get("dataset", []) for p in d.get("point", []) for v in p.get("value", []))
            resultados[data_inicio] = total
        return resultados
    except Exception as e:
        print("Erro ao obter passos:", e)
        return {}

# Batimentos Médios

def obter_batimentos_medios(token, inicio, fim):
    url = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "aggregateBy": [{"dataTypeName": "com.google.heart_rate.bpm"}],
        "bucketByTime": {"durationMillis": 86400000},
        "startTimeMillis": int(inicio.strftime("%s")) * 1000,
        "endTimeMillis": int(fim.strftime("%s")) * 1000
    }
    try:
        response = requests.post(url, headers=headers, json=body)
        data = response.json()
        resultados = {}
        for bucket in data.get("bucket", []):
            data_inicio = datetime.fromtimestamp(int(bucket["startTimeMillis"]) / 1000).date()
            total, count = 0, 0
            for dataset in bucket["dataset"]:
                for point in dataset.get("point", []):
                    for val in point.get("value", []):
                        total += val.get("fpVal", 0)
                        count += 1
            resultados[data_inicio] = round(total / count, 1) if count else 0
        return resultados
    except Exception as e:
        print("Erro ao obter batimentos:", e)
        return {}

# Dados de Sono

def obter_sono(token, inicio, fim):
    url = "https://www.googleapis.com/fitness/v1/users/me/sessions"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "startTime": inicio.isoformat() + "T00:00:00Z",
        "endTime": fim.isoformat() + "T23:59:59Z"
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        resultados = {}
        for sessao in data.get("session", []):
            if sessao.get("activityType") == 72:  # Sono
                inicio_sessao = datetime.fromisoformat(sessao["startTimeMillis"]) if "startTimeMillis" in sessao else None
                fim_sessao = datetime.fromisoformat(sessao["endTimeMillis"]) if "endTimeMillis" in sessao else None
                if inicio_sessao and fim_sessao:
                    duracao_horas = round((fim_sessao - inicio_sessao).total_seconds() / 3600, 2)
                    dia = inicio_sessao.date()
                    resultados[dia] = resultados.get(dia, 0) + duracao_horas
        return resultados
    except Exception as e:
        print("Erro ao obter sono:", e)
        return {}

# Último peso e altura

def obter_ultimo_peso(token):
    url = "https://www.googleapis.com/fitness/v1/users/me/dataSources/derived:com.google.weight:com.google.android.gms:merge_weight/datasets/0-9999999999999"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        pontos = data.get("point", [])
        if pontos:
            valor = pontos[-1].get("value", [{}])[0].get("fpVal")
            return round(valor, 2) if valor else None
    except Exception as e:
        print("Erro ao obter peso:", e)
    return None

def obter_ultima_altura(token):
    url = "https://www.googleapis.com/fitness/v1/users/me/dataSources/derived:com.google.height:com.google.android.gms:merge_height/datasets/0-9999999999999"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        pontos = data.get("point", [])
        if pontos:
            valor = pontos[-1].get("value", [{}])[0].get("fpVal")
            return round(valor, 2) if valor else None
    except Exception as e:
        print("Erro ao obter altura:", e)
    return None
