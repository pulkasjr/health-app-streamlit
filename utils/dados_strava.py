import requests
from polyline import decode
import folium

def buscar_ultimas_atividades(token):
    url = 'https://www.strava.com/api/v3/athlete/activities'
    headers = {'Authorization': f'Bearer {token}'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        atividades = []
        atleta_id = None
        for item in response.json():
            if not atleta_id and "athlete" in item:
                atleta_id = item["athlete"].get("id")
            
            atividade = {
                'nome': item.get('name'),
                'distancia_km': round(item.get('distance', 0) / 1000, 2),
                'duracao_min': round(item.get('moving_time', 0) / 60, 1),
                'tipo': item.get('type'),
                'mapa': item.get('map', {}).get('summary_polyline')
            }
            atividades.append(atividade)
        return atividades, atleta_id
    except requests.RequestException as e:
        print(f"ERRO: Falha ao buscar atividades do Strava: {e}")
        return [], None

def buscar_estatisticas_atleta(token, atleta_id):
    url = f'https://www.strava.com/api/v3/athletes/{atleta_id}/stats'
    headers = {'Authorization': f'Bearer {token}'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        stats = response.json()
        return {
            'corrida_distancia_km': round(stats.get('ytd_run_totals', {}).get('distance', 0) / 1000, 1),
            'pedalada_distancia_km': round(stats.get('ytd_ride_totals', {}).get('distance', 0) / 1000, 1)
        }
    except requests.RequestException as e:
        print(f"ERRO: Falha ao buscar estatísticas do Strava: {e}")
        return None

def gerar_mapa_atividade(atividade):
    polyline_str = atividade.get("mapa")
    if not polyline_str:
        return "<p style='text-align: center; margin-top: 50px;'>Sem mapa disponível para esta atividade.</p>"

    try:
        coordenadas = decode(polyline_str)
        if not coordenadas:
             return "<p style='text-align: center; margin-top: 50px;'>Mapa sem coordenadas.</p>"
        
        mapa = folium.Map(location=coordenadas[0], zoom_start=13, tiles="CartoDB positron")
        folium.PolyLine(locations=coordenadas, color="#FC4C02", weight=3).add_to(mapa)
        return mapa._repr_html_()
    except Exception as e:
        return f"<p>Erro ao gerar mapa: {e}</p>"