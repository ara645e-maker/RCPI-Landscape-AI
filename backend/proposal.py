import base64
from io import BytesIO


def _safe_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).replace('₹', 'Rs.').replace('₹', 'Rs.')


def generate_pdf_proposal(project_name: str, analysis_details: dict) -> str:
    try:
        from fpdf import FPDF
    except ImportError:
        return _generate_simple_pdf_fallback(project_name, analysis_details)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f'Project Proposal: {project_name}', ln=True)
    pdf.ln(5)

    pdf.set_font('Arial', '', 12)
    pdf.multi_cell(0, 8, _safe_text(f"Summary: {analysis_details.get('summary', 'N/A')}"))
    pdf.ln(2)
    pdf.multi_cell(0, 8, _safe_text(f"Space type: {analysis_details.get('space_type', 'N/A')}"))
    pdf.multi_cell(0, 8, _safe_text(f"Sunlight: {analysis_details.get('sunlight', 'N/A')}"))
    pdf.multi_cell(0, 8, _safe_text(f"Soil condition: {analysis_details.get('soil_condition', 'N/A')}"))
    pdf.multi_cell(0, 8, _safe_text(f"Area (sqft): {analysis_details.get('area_sqft', 'N/A')}"))
    pdf.ln(4)

    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Plant Selection', ln=True)
    pdf.set_font('Arial', '', 11)
    for plant in analysis_details.get('plant_selection', []):
        pdf.multi_cell(0, 7, _safe_text(f"- {plant.get('common_name', '')} ({plant.get('botanical_name', '')}), Reason: {plant.get('reason', '')}"))
    pdf.ln(4)

    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'BOQ', ln=True)
    pdf.set_font('Arial', '', 11)
    for item in analysis_details.get('boq', []):
        pdf.multi_cell(0, 7, _safe_text(f"- {item.get('item', '')}: {item.get('quantity', '')} @ {item.get('unit_cost_inr', '')} = {item.get('total_cost_inr', '')}"))
    pdf.ln(4)

    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Proposal Terms', ln=True)
    pdf.set_font('Arial', '', 11)
    for term in analysis_details.get('terms', []):
        pdf.multi_cell(0, 7, _safe_text(f"- {term}"))
    pdf.ln(4)

    output = BytesIO()
    try:
        pdf.output(output)
    except Exception:
        return _generate_simple_pdf_fallback(project_name, analysis_details)

    output.seek(0)
    try:
        return base64.b64encode(output.read()).decode('utf-8')
    except Exception:
        return _generate_simple_pdf_fallback(project_name, analysis_details)


def _generate_simple_pdf_fallback(project_name: str, analysis_details: dict) -> str:
    lines = [
        f"Project Proposal: {project_name}",
        f"Summary: {analysis_details.get('summary', 'N/A')}",
        f"Space type: {analysis_details.get('space_type', 'N/A')}",
        f"Sunlight: {analysis_details.get('sunlight', 'N/A')}",
        f"Soil condition: {analysis_details.get('soil_condition', 'N/A')}",
        f"Area (sqft): {analysis_details.get('area_sqft', 'N/A')}",
        "",
        "Plant Selection:",
    ]
    for plant in analysis_details.get('plant_selection', []):
        lines.append(f"- {plant.get('common_name', '')} ({plant.get('botanical_name', '')})")
    lines.extend(["", "BOQ:"])
    for item in analysis_details.get('boq', []):
        lines.append(f"- {item.get('item', '')}: {item.get('quantity', '')}")
    lines.extend(["", "Proposal Terms:"])
    for term in analysis_details.get('terms', []):
        lines.append(f"- {term}")

    content = "\n".join(lines).encode('utf-8')
    return base64.b64encode(content).decode('utf-8')
