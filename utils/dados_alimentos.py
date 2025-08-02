# utils/dados_alimentos.py
import requests

def buscar_info_alimento(nome):
    """Busca informações detalhadas de um alimento na API Open Food Facts."""
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={nome}&search_simple=1&action=process&json=1"
    try:
        r = requests.get(url)
        r.raise_for_status()
        produtos = r.json().get("products", [])
        if not produtos:
            return None

        # Pega o primeiro produto da lista de resultados
        p = produtos[0]
        nutriments = p.get("nutriments", {})
        
        return {
            "nome": p.get("product_name_pt", p.get("product_name", "Nome não encontrado")),
            "imagem": p.get("image_front_url"),
            "nutriscore": p.get("nutriscore_grade", "?"),
            
            # --- NOVOS CAMPOS ---
            "nova_group": p.get("nova_group"), # Classificação de processamento (1, 2, 3 ou 4)
            "ingredientes": p.get("ingredients_text_pt", p.get("ingredients_text", "Não listados")),
            
            # --- Macronutrientes ---
            "calorias": nutriments.get("energy-kcal_100g", 0),
            "gordura": nutriments.get("fat_100g", 0),
            "gordura_saturada": nutriments.get("saturated-fat_100g", 0),
            "carboidratos": nutriments.get("carbohydrates_100g", 0),
            "açucar": nutriments.get("sugars_100g", 0),
            "fibras": nutriments.get("fiber_100g", 0),
            "proteinas": nutriments.get("proteins_100g", 0),
            "sal": nutriments.get("salt_100g", 0)
        }
    except requests.RequestException as e:
        print(f"Erro ao buscar dados de alimentos: {e}")
        return None

def gerar_dicas_nutricionais(dados):
    """Gera dicas de saúde com base nos dados nutricionais."""
    dicas = []
    # Dica baseada no Grupo NOVA (nível de processamento)
    if dados.get("nova_group") == 4:
        dicas.append("🔴 **Atenção:** Este é um alimento ultraprocessado (NOVA 4). Consuma com moderação.")
    elif dados.get("nova_group") == 3:
        dicas.append("🟡 **Cuidado:** Este é um alimento processado (NOVA 3).")

    # Dica baseada no Nutri-Score
    if dados.get("nutriscore", "?").lower() in ["d", "e"]:
        dicas.append("⚠️ O Nutri-Score deste alimento é baixo. Prefira opções mais saudáveis.")
    
    if dados.get("açucar", 0) > 15:
        dicas.append("🔻 Este alimento é rico em açúcar. Reduza o consumo.")
    if dados.get("gordura_saturada", 0) > 5:
        dicas.append("🔻 Alto teor de gordura saturada. Consuma com moderação.")
    
    if len(dicas) == 0:
        dicas.append("✅ Parece uma escolha nutricional equilibrada.")

    return dicas