import json
from pathlib import Path
from typing import Dict, List

DATA_PATH = Path(__file__).resolve().parent / "data" / "indian_landscape_brain.json"


def load_brain() -> Dict:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def analyze_space(discovery: Dict) -> Dict:
    return discovery


def design_concept(discovery: Dict, preferred_style: str) -> str:
    style = preferred_style
    if discovery["space_type"] == "Balcony":
        style = "Balcony Oasis"
    elif discovery["space_type"] == "Rooftop":
        style = "Minimalist Terrace Garden"
    elif discovery["space_type"] == "Lawn":
        style = "Modern Indian Garden"
    return style


def search_plants(discovery: Dict, brain: Dict, style: str, top_n: int = 6) -> List[Dict]:
    candidates = []
    query_tokens = [style.lower(), discovery["sunlight"].lower(), discovery["space_type"].lower(), discovery["soil_condition"].lower()]
    for plant in brain["flora"]:
        score = 0
        if discovery["sunlight"] in plant["sunlight"]:
            score += 3
        if discovery["space_type"] in plant["placement"]:
            score += 3
        if any(token in plant["description"].lower() for token in query_tokens):
            score += 2
        if discovery["soil_condition"] == "Dry" and plant["water"].lower() == "low":
            score += 1
        if "balcony" in style.lower() and any("balcony" in p.lower() for p in plant["placement"]):
            score += 2
        candidates.append((score, plant))

    candidates.sort(key=lambda item: item[0], reverse=True)
    selected = [plant for score, plant in candidates if score > 0]
    if not selected:
        selected = [plant for _, plant in candidates[:top_n]]
    return selected[:top_n]


def build_rag_prompt(discovery: Dict, style: str, plant_candidates: List[Dict], brain: Dict, retrieved_docs: List[Dict]) -> str:
    plant_lines = []
    for plant in plant_candidates:
        sunlight = ", ".join(plant.get("sunlight", []))
        placement = ", ".join(plant.get("placement", []))
        description = plant.get("description", "No description available")
        plant_lines.append(
            f"{plant.get('common_name', 'Unknown')} ({plant.get('botanical_name', 'Unknown')}) Hindi: {plant.get('hindi_name', 'N/A')}. "
            f"Sunlight: {sunlight}. Water: {plant.get('water', 'N/A')}. Height: {plant.get('height_m', 'N/A')}. "
            f"Growth: {plant.get('growth', 'N/A')}. Maintenance: {plant.get('maintenance', 'N/A')}. Placement: {placement}. "
            f"Description: {description}"
        )

    rates = brain["cpwd_rates"]
    rate_lines = [f"{key.replace('_', ' ').title()}: ₹{value}" for key, value in rates.items()]

    retrieved_lines = []
    for doc in retrieved_docs:
        retrieved_lines.append(f"- {doc['type'].title()}: {doc['text']}")

    return (
        "You are a local Indian landscaping assistant. Use only the following embedded plant knowledge, retrieved local cost/labor context, and rate data to make recommendations. "
        "Do not invent plants or cost rules that are not listed. Focus on Indian garden sensibilities, regional planting, and accurate CPWD-style cost estimation.\n\n"
        f"Site summary: Space type: {discovery['space_type']}, Sunlight: {discovery['sunlight']}, Soil: {discovery['soil_condition']}, Preferred style: {style}.\n\n"
        "Plant knowledge base:\n"
        + "\n".join(plant_lines)
        + "\n\nRetrieved RAG context:\n"
        + "\n".join(retrieved_lines)
        + "\n\nRate sheet:\n"
        + "\n".join(rate_lines)
        + "\n\nGenerate a concise strategy for the landscape design, explain why these plants fit, and confirm the execution focus for the Indian context."
    )


def build_render_prompt(discovery: Dict, style: str, plant_selection: List[Dict]) -> str:
    plant_names = ", ".join([plant["common_name"] for plant in plant_selection])
    return (
        f"Create a photorealistic Indian landscaping design for a {discovery['space_type']} space with {discovery['sunlight']} exposure and {discovery['soil_condition']} soil. "
        f"Style should be {style}, with lush native plants such as {plant_names}. Include warm terracotta textures, modern stone pathways, traditional Indian garden accents, soft lighting, and tropical greenery. "
        "Render as a high-resolution realistic outdoor landscape photograph."
    )


def select_plants(discovery: Dict, plant_candidates: List[Dict], style: str) -> List[Dict]:
    selected = []
    for plant in plant_candidates[:5]:
        selected.append({
            "botanical_name": plant["botanical_name"],
            "common_name": plant["common_name"],
            "hindi_name": plant["hindi_name"],
            "sunlight": plant["sunlight"],
            "water": plant["water"],
            "height_m": plant["height_m"],
            "growth": plant["growth"],
            "maintenance": plant["maintenance"],
            "placement": plant["placement"],
            "reason": f"Selected for {style} and compatibility with {discovery['sunlight']} exposure.",
        })
    return selected


def estimate_boq(area_sqft: float, plant_selection: List[Dict], brain: Dict, style: str):
    base_rates = brain["cpwd_rates"]
    plant_cost = 0
    boq = []
    for plant in plant_selection:
        unit_cost = base_rates.get("plant_unit_cost", 90)
        qty = max(2, int(area_sqft / 50))
        item_cost = unit_cost * qty
        plant_cost += item_cost
        boq.append({
            "item": f"{plant['common_name']} ({plant['botanical_name']})",
            "quantity": f"{qty} nos",
            "unit_cost_inr": f"₹{unit_cost}",
            "total_cost_inr": f"₹{item_cost}",
        })

    soil_cost = int(base_rates["soil_per_cuft"] * 1.5 * area_sqft / 10)
    fertilizer_cost = int(base_rates["fertilizer_per_kg"] * 5)
    grass_cost = int(base_rates["turf_per_sqft"] * area_sqft)
    labor_cost = int(base_rates["labor_per_sqft"] * area_sqft)
    irrigation_cost = int(base_rates["irrigation_per_sqft"] * area_sqft * 0.5)

    boq.extend([
        {"item": "Topsoil & Compost mix", "quantity": f"{int(area_sqft / 10)} cuft", "unit_cost_inr": f"₹{base_rates['soil_per_cuft']}", "total_cost_inr": f"₹{soil_cost}"},
        {"item": "Organic fertilizer set", "quantity": "5 kg", "unit_cost_inr": f"₹{base_rates['fertilizer_per_kg']}", "total_cost_inr": f"₹{fertilizer_cost}"},
        {"item": "Turf / Grass cover", "quantity": f"{int(area_sqft)} sq ft", "unit_cost_inr": f"₹{base_rates['turf_per_sqft']}", "total_cost_inr": f"₹{grass_cost}"},
        {"item": "Labor & execution", "quantity": f"{int(area_sqft)} sq ft", "unit_cost_inr": f"₹{base_rates['labor_per_sqft']}", "total_cost_inr": f"₹{labor_cost}"},
        {"item": "Basic irrigation / drip layout", "quantity": f"{int(area_sqft)} sq ft", "unit_cost_inr": f"₹{base_rates['irrigation_per_sqft']}", "total_cost_inr": f"₹{irrigation_cost}"},
    ])

    total_cost = plant_cost + soil_cost + fertilizer_cost + grass_cost + labor_cost + irrigation_cost
    return boq, total_cost


def estimate_timeline(area_sqft: float, style: str) -> int:
    base_days = 3
    size_factor = int(area_sqft / 100)
    style_factor = 2 if "Modern" in style or "Hardscape" in style else 1
    return max(2, base_days + size_factor + style_factor)


def generate_terms(area_sqft: float, style: str) -> List[str]:
    return [
        "Payment terms: 40% advance, 40% on material delivery, 20% on completion.",
        f"Project scope includes landscape layout, planting, soil preparation, turfing, and drip irrigation for {int(area_sqft)} sq ft.",
        "Any changes in material specification or scope will require a written change order.",
        "Client to provide clear access and electricity for project execution.",
        "Guarantee: plants are covered for 30 days for establishment; external factors such as weather are excluded.",
    ]
