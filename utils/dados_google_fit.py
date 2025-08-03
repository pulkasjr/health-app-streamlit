# CÓDIGO FINAL E CORRETO PARA utils/dados_google_fit.py (SEM IMPORTAÇÃO CIRCULAR)

import time
from datetime import datetime, timedelta

# Esta biblioteca é usada para construir o serviço da API
# Se não a tiver, instale com: pip install google-api-python-client
from googleapiclient.discovery import build

def build_service(credentials):
    """Cria o objeto de serviço da API do Google Fitness."""
    return build('fitness', 'v1', credentials=credentials)

def obter_passos_diarios(credentials):
    """Obtém a contagem de passos dos últimos 7 dias."""
    service = build_service(credentials)
    end_time_ms = int(time.time() * 1000)
    start_time_ms = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)

    try:
        response = service.users().dataset().aggregate(
            userId='me',
            body={
                'aggregateBy': [{'dataTypeName': 'com.google.step_count.delta', 'dataSourceId': 'derived:com.google.step_count.delta:com.google.android.gms:estimated_steps'}],
                'bucketByTime': {'durationMillis': 86400000},
                'startTimeMillis': start_time_ms,
                'endTimeMillis': end_time_ms
            }
        ).execute()
        
        passos_dict = {}
        for bucket in response.get('bucket', []):
            points = bucket.get('dataset', [{}])[0].get('point', [])
            if points and points[0].get('value', [{}])[0].get('intVal') is not None:
                dia = datetime.fromtimestamp(int(points[0]['startTimeNanos']) / 1e9).strftime('%Y-%m-%d')
                passos_dict[dia] = points[0]['value'][0]['intVal']
        return passos_dict
    except Exception as e:
        print(f"Erro ao obter passos diários: {e}")
        return {}

def obter_batimentos_medios(credentials):
    """Obtém a média de batimentos cardíacos dos últimos 7 dias."""
    service = build_service(credentials)
    end_time_ms = int(time.time() * 1000)
    start_time_ms = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)

    try:
        response = service.users().dataset().aggregate(
            userId='me',
            body={
                'aggregateBy': [{'dataTypeName': 'com.google.heart_rate.bpm', 'dataSourceId': 'derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm'}],
                'bucketByTime': {'durationMillis': 86400000},
                'startTimeMillis': start_time_ms,
                'endTimeMillis': end_time_ms
            }
        ).execute()

        bpm_dict = {}
        for bucket in response.get('bucket', []):
            points = bucket.get('dataset', [{}])[0].get('point', [])
            if points and points[0].get('value', [{}])[0].get('fpVal') is not None:
                dia = datetime.fromtimestamp(int(points[0]['startTimeNanos']) / 1e9).strftime('%Y-%m-%d')
                bpm_dict[dia] = round(points[0]['value'][0]['fpVal'])
        return bpm_dict
    except Exception as e:
        print(f"Erro ao obter batimentos médios: {e}")
        return {}

def obter_sono(credentials):
    """Obtém as horas de sono dos últimos 7 dias."""
    service = build_service(credentials)
    end_time_ns = int(time.time() * 1e9)
    start_time_ns = int((datetime.now() - timedelta(days=7)).timestamp() * 1e9)
    
    try:
        response = service.users().sessions().list(userId='me', activityType=72, startTime=f"{datetime.fromtimestamp(start_time_ns/1e9).isoformat()}Z", endTime=f"{datetime.fromtimestamp(end_time_ns/1e9).isoformat()}Z").execute()
        
        sono_dict = {}
        for session in response.get('session', []):
            start_millis = int(session['startTimeMillis'])
            end_millis = int(session['endTimeMillis'])
            dia = datetime.fromtimestamp(start_millis / 1000).strftime('%Y-%m-%d')
            duracao_horas = (end_millis - start_millis) / (1000 * 60 * 60)
            sono_dict[dia] = sono_dict.get(dia, 0) + duracao_horas
        
        return {k: round(v, 1) for k, v in sono_dict.items()}
    except Exception as e:
        print(f"Erro ao obter dados de sono: {e}")
        return {}

def obter_ultimo_dado(service, data_source_id):
    """Função auxiliar para buscar o ponto de dados mais recente."""
    end_time_ns = int(time.time() * 1e9)
    start_time_ns = int((datetime.now() - timedelta(days=365)).timestamp() * 1e9)
    dataset_id = f"{start_time_ns}-{end_time_ns}"

    try:
        response = service.users().dataSources().datasets().get(userId='me', dataSourceId=data_source_id, datasetId=dataset_id).execute()
        points = response.get('point', [])
        return points[-1] if points else None
    except Exception as e:
        print(f"Erro ao buscar último dado para {data_source_id}: {e}")
        return None

def obter_ultimo_peso(credentials):
    """Busca o registro de peso mais recente."""
    service = build_service(credentials)
    data_source_id = "derived:com.google.weight:com.google.android.gms:merge_weight"
    ultimo_dado = obter_ultimo_dado(service, data_source_id)
    if ultimo_dado and 'value' in ultimo_dado and ultimo_dado['value']:
        return ultimo_dado['value'][0].get('fpVal')
    return None

def obter_ultima_altura(credentials):
    """Busca o registro de altura mais recente."""
    service = build_service(credentials)
    data_source_id = "derived:com.google.height:com.google.android.gms:merge_height"
    ultimo_dado = obter_ultimo_dado(service, data_source_id)
    if ultimo_dado and 'value' in ultimo_dado and ultimo_dado['value']:
        return ultimo_dado['value'][0].get('fpVal')
    return None