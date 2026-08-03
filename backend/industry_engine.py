import json
from pathlib import Path
from typing import Dict, List, Tuple


def load_horticulture_data() -> Dict:
    path = Path(__file__).resolve().parent / "data" / "horticulture_industry_data.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_design_methodology() -> Dict:
    path = Path(__file__).resolve().parent / "data" / "design_methodology.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_industry_context(discovery: Dict, style: str, area_sqft: float, industry_data: Dict) -> str:
    workflow = " -> ".join([step["step"] for step in industry_data["execution_workflow"]])
    contract_models = industry_data["contract_models"]
    terms = industry_data["deal_terms"]
    procurement = ", ".join([hub["name"] for hub in industry_data["nursery_hubs"]])
    return (
        f"Execute the project using a proven Indian site preparation workflow: {workflow}. "
        f"Use both itemized and turnkey lump-sum contracting models with a 10% wastage buffer for soil and turf. "
        f"Seasonal pricing must reflect monsoon, winter, and summer nursery conditions. "
        f"Prefer local nursery hubs such as {procurement} based on regional plant availability. "
        f"Include these commercial terms: {'; '.join(terms)}"
    )


def calculate_industry_boq(area_sqft: float, plant_selection: List[Dict], industry_data: Dict, seasonal_factor: float = 1.0) -> Tuple[List[Dict], float]:
    rates = industry_data["pricing_rules"]
    boq = []

    cleanup_cost = int(rates["cleanup_per_sqft"] * area_sqft * seasonal_factor)
    soil_qty = int(area_sqft * 0.1 * (1 + rates["soil_wastage_pct"] / 100))
    soil_cost = int(rates["soil_per_cuft"] * soil_qty * seasonal_factor)
    turf_qty = int(area_sqft * (1 + rates["turf_wastage_pct"] / 100))
    turf_cost = int(rates["turf_per_sqft"] * turf_qty * seasonal_factor)
    hardscape_cost = int(rates["hardscape_per_sqft"] * area_sqft * seasonal_factor * 0.4)
    drainage_cost = int(rates["drainage_per_sqft"] * area_sqft * seasonal_factor * 0.2)
    irrigation_cost = int(rates["irrigation_per_sqft"] * area_sqft * seasonal_factor)
    labor_cost = int(rates["labor_per_sqft"] * area_sqft * seasonal_factor)

    plant_cost = 0
    for plant in plant_selection:
        unit_cost = 90
        qty = max(2, int(area_sqft / 50))
        item_cost = unit_cost * qty
        plant_cost += item_cost
        boq.append({
            "item": f"Plants: {plant['common_name']} ({plant['botanical_name']})",
            "quantity": f"{qty} nos",
            "unit_cost_inr": f"₹{unit_cost}",
            "total_cost_inr": f"₹{item_cost}"
        })

    boq.extend([
        {"item": "Site Cleanup & Debris Removal", "quantity": f"{int(area_sqft)} sq ft", "unit_cost_inr": f"₹{rates['cleanup_per_sqft']}", "total_cost_inr": f"₹{cleanup_cost}"},
        {"item": "Soil Preparation & Manure Mixing", "quantity": f"{soil_qty} cu ft", "unit_cost_inr": f"₹{rates['soil_per_cuft']}", "total_cost_inr": f"₹{soil_cost}"},
        {"item": "Drainage Setup & Hardscape Edging", "quantity": f"{int(area_sqft * 0.2)} sq ft", "unit_cost_inr": f"₹{rates['drainage_per_sqft']}", "total_cost_inr": f"₹{drainage_cost}"},
        {"item": "Hardscaping & Edging", "quantity": f"{int(area_sqft * 0.4)} sq ft", "unit_cost_inr": f"₹{rates['hardscape_per_sqft']}", "total_cost_inr": f"₹{hardscape_cost}"},
        {"item": "Turf Laying with 10% Buffer", "quantity": f"{turf_qty} sq ft", "unit_cost_inr": f"₹{rates['turf_per_sqft']}", "total_cost_inr": f"₹{turf_cost}"},
        {"item": "Drip Install & Commissioning", "quantity": f"{int(area_sqft)} sq ft", "unit_cost_inr": f"₹{rates['irrigation_per_sqft']}", "total_cost_inr": f"₹{irrigation_cost}"},
        {"item": "Initial Watering & Settling", "quantity": "1 service", "unit_cost_inr": "₹0", "total_cost_inr": "₹0"},
        {"item": "Labor & Project Execution", "quantity": f"{int(area_sqft)} sq ft", "unit_cost_inr": f"₹{rates['labor_per_sqft']}", "total_cost_inr": f"₹{labor_cost}"}
    ])

    subtotal = cleanup_cost + soil_cost + drainage_cost + hardscape_cost + turf_cost + irrigation_cost + labor_cost + plant_cost
    contingency = int(subtotal * rates["contingency_pct"] / 100)
    total_cost = subtotal + contingency

    boq.append({
        "item": "Contingency Buffer",
        "quantity": f"{rates['contingency_pct']}%",
        "unit_cost_inr": "₹0",
        "total_cost_inr": f"₹{contingency}"
    })

    return boq, total_cost


def build_layout_blueprint(discovery: Dict, style: str, plant_selection: List[Dict], design_data: Dict) -> Dict:
    style_guidance = design_data["styles"].get(style, {})
    instructions = []
    instructions.append(f"Use {style} principles with {style_guidance.get('palette', 'a balanced seasonal palette')}." )
    instructions.append(f"Follow planting layers: {', '.join(design_data['planting_layers'])}.")
    instructions.append("Maintain hardscape to softscape ratio approximately 25:60 with remaining utility space.")

    if discovery["space_type"] == "Lawn":
        instructions.append("Place the main specimen tree at the north-east focal point and keep circulation paths to the south.")
    elif discovery["space_type"] == "Balcony":
        instructions.append("Use vertical climbers and container layers with accent foliage at eye level.")
    else:
        instructions.append("Organize seating and water feature near the center with perimeter planting for privacy.")

    placements = []
    if plant_selection:
        primary = plant_selection[0]
        placements.append(f"Place {primary['common_name']} at the main focal point.")
        if len(plant_selection) > 1:
            placements.append(f"Run a hedge of {plant_selection[1]['common_name']} along the east boundary.")
        if len(plant_selection) > 2:
            placements.append(f"Use {plant_selection[2]['common_name']} as mid-layer accents behind the groundcover.")

    return {
        "style": style,
        "guidance": instructions,
        "placements": placements,
        "zoning": design_data["zoning"],
        "rules": design_data["layout_rules"]
    }


def choose_seasonal_factor(season: str, industry_data: Dict) -> float:
    return industry_data["pricing_rules"]["seasonal_variations"].get(season.lower(), 1.0)
