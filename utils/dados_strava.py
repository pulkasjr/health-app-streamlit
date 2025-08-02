# utils/dados_strava.py
import requests
import json
import os
import time
import folium
import polyline

def obter_token_valido(client_id, client_secret, token_file):
    if not os.path.exists(token_file):
        return None

    with open(token_file, "r") as f:
        tokens = json.load(f)

    if time.time() > tokens.get("expires_at", 0):
        print("🔄 Atualizando token do Strava...")
        response = requests.post("https://www.strava.com/oauth/token", data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": tokens.get("refresh_token")
        })
        if response.ok:
            new_tokens = response.json()
            tokens.update({
                "access_token": new_tokens["access_token"],
                "expires_at": new_tokens["expires_at"],
                "refresh_token": new_tokens.get("refresh_token", tokens["refresh_token"])
            })
            with open(token_file, "w") as f:
                json.dump(tokens, f)
            print("✅ Tokens do Strava salvos.")
        else:
            print("Erro ao atualizar token do Strava:", response.text)
            return None
    return tokens.get("access_token")

def salvar_tokens(tokens, token_file):
    with open(token_file, "w") as f:
        json.dump(tokens, f)


def buscar_ultimas_atividades(token):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get("https://www.strava.com/api/v3/athlete/activities", headers=headers)
    if r.status_code == 200:
        atividades = []
        for a in r.json():
            atividades.append({
                "id": a["id"],
                "nome": a.get("name"),
                "distancia_km": round(a.get("distance", 0) / 1000, 2),
                "duracao_min": round(a.get("elapsed_time", 0) / 60, 1),
                "mapa": a.get("map", {}).get("summary_polyline", "")
            })
        atleta_id = atividades[0].get("id") if atividades else None
        return atividades, atleta_id
    return [], None

def gerar_mapa_atividade(atividade):
    if not atividade.get("mapa"):
        return ""
    coordenadas = polyline.decode(atividade["mapa"])
    if not coordenadas:
        return ""
    m = folium.Map(location=coordenadas[0], zoom_start=13)
    folium.PolyLine(coordenadas, color="blue", weight=5).add_to(m)
    return m._repr_html_()

def buscar_estatisticas_atleta(token, atleta_id=None):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get("https://www.strava.com/api/v3/athlete/stats", headers=headers)
    if r.status_code == 200:
        stats = r.json()
        return {
            "corrida_distancia_km": round(stats["ytd_run_totals"]["distance"] / 1000, 1),
            "pedalada_distancia_km": round(stats["ytd_ride_totals"]["distance"] / 1000, 1)
        }
    return None
