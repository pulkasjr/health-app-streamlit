import requests

def buscar_info_alimento(nome):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={nome}&search_simple=1&action=process&json=1"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    produtos = r.json().get("products", [])
    if not produtos:
        return None

    p = produtos[0]
    return {
        "nome": p.get("product_name", "Desconhecido"),
        "imagem": p.get("image_front_url"),
        "calorias": p.get("nutriments", {}).get("energy-kcal_100g", 0),
        "açucar": p.get("nutriments", {}).get("sugars_100g", 0),
        "gordura": p.get("nutriments", {}).get("fat_100g", 0),
        "sal": p.get("nutriments", {}).get("salt_100g", 0),
        "nutriscore": p.get("nutriscore_grade", "?")
    }

def gerar_dicas_nutricionais(dados):
    dicas = []
    if dados["nutriscore"] in ["a", "b"]:
        dicas.append("✅ Alimento com bom Nutri-Score, ótimo para consumo regular.")
    else:
        dicas.append("⚠️ Evite consumo frequente — Nutri-Score não é favorável.")

    if dados["açucar"] > 10:
        dicas.append("🔻 Reduza o consumo por conter muito açúcar.")
    if dados["gordura"] > 10:
        dicas.append("🔻 Alto teor de gordura, consuma com moderação.")
    if dados["sal"] > 1:
        dicas.append("🔻 Contém muito sal, atenção à pressão arterial.")
    if not dicas:
        dicas.append("✅ Este alimento tem bons valores nutricionais gerais.")

    return dicas
