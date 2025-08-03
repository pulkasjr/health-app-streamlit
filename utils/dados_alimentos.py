import requests

def buscar_info_alimento(nome):
    """Busca informações de um alimento na API Open Food Facts."""
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={nome}&search_simple=1&action=process&json=1"
    try:
        r = requests.get(url)
        r.raise_for_status()
        produtos = r.json().get("products", [])
        if not produtos:
            return None

        p = produtos[0]
        nutriments = p.get("nutriments", {})
        
        return {
            "nome": p.get("product_name_pt", p.get("product_name", "Nome não encontrado")),
            "imagem": p.get("image_front_url"),
            "nutriscore": p.get("nutriscore_grade", "?"),
            "nova_group": p.get("nova_group"),
            "ingredientes": p.get("ingredients_text_pt", p.get("ingredients_text", "Não listados")),
            "calorias": nutriments.get("energy-kcal_100g"),
            "gordura": nutriments.get("fat_100g"),
            "gordura_saturada": nutriments.get("saturated-fat_100g"),
            "carboidratos": nutriments.get("carbohydrates_100g"),
            "açucar": nutriments.get("sugars_100g"),
            "fibras": nutriments.get("fiber_100g"),
            "proteinas": nutriments.get("proteins_100g"),
            "sal": nutriments.get("salt_100g")
        }
    except requests.RequestException as e:
        print(f"ERRO (dados_alimentos.py): Falha ao buscar dados de alimentos: {e}")
        return None

def gerar_dicas_nutricionais(dados):
    """Gera dicas de saúde com base nos dados nutricionais."""
    dicas = []
    if dados.get("nova_group") == 4:
        dicas.append("🔴 **Atenção:** Este é um alimento ultraprocessado (NOVA 4). Consuma com moderação.")
    elif dados.get("nova_group") == 3:
        dicas.append("🟡 **Cuidado:** Este é um alimento processado (NOVA 3).")

    if dados.get("nutriscore", "?").lower() in ["d", "e"]:
        dicas.append("⚠️ O Nutri-Score deste alimento é baixo. Prefira opções mais saudáveis.")
    
    if dados.get("açucar") is not None and dados.get("açucar", 0) > 15:
        dicas.append("🔻 Este alimento é rico em açúcar. Reduza o consumo.")
    if dados.get("gordura_saturada") is not None and dados.get("gordura_saturada", 0) > 5:
        dicas.append("🔻 Alto teor de gordura saturada. Consuma com moderação.")
    
    if not dicas:
        dicas.append("✅ Parece uma escolha nutricional equilibrada.")

    return dicas