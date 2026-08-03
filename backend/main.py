import json
import os
import shutil
import sys
from pathlib import Path
from typing import List

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.auth import create_access_token
from backend.brain import (
    load_brain,
    design_concept,
    search_plants,
    build_rag_prompt,
    select_plants,
    estimate_timeline,
    generate_terms,
    build_render_prompt,
)
from backend.crud import (
    add_credits,
    authenticate_user,
    create_project,
    create_user,
    deduct_credits,
    get_all_projects,
    get_all_users,
    get_project,
    get_projects_for_user,
    get_user_by_email,
    save_project_analysis,
)
from backend.database import init_db
from backend.dependencies import get_current_active_user, get_current_admin_user, get_db
from backend.industry_engine import (
    load_horticulture_data,
    load_design_methodology,
    build_industry_context,
    calculate_industry_boq,
    build_layout_blueprint,
    choose_seasonal_factor,
)
from backend.llm_client import describe_space, generate_chat_response
from backend.payment import simulate_payment
from backend.proposal import generate_pdf_proposal
from backend.rag_store import RAGStore
from backend.schemas import (
    AnalysisResponse,
    ChatRequest,
    ChatResponse,
    PaymentRequest,
    PaymentResponse,
    ProjectCreate,
    ProjectResponse,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
)
from backend.stable_diffusion import generate_design_render
from backend.image_analyzer import analyze_image

app = FastAPI(title="Rahega Landscape AI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BRAIN = load_brain()
HORTICULTURE_DATA = load_horticulture_data()
DESIGN_DATA = load_design_methodology()
RAG_STORE = RAGStore(
    [
        Path(__file__).resolve().parent / "data" / "indian_landscape_rag.json",
        Path(__file__).resolve().parent / "data" / "horticulture_industry_data.json",
        Path(__file__).resolve().parent / "data" / "design_methodology.json",
    ],
    Path(__file__).resolve().parent / "data" / "rag_embeddings.npy",
)
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ANALYSIS_CREDIT_COST = int(os.environ.get("ANALYSIS_CREDIT_COST", 5))
CREDIT_TOPUP_RATE = int(os.environ.get("CREDIT_TOPUP_RATE", 100))


@app.on_event("startup")
def startup_event():
    init_db()


def build_analysis_response(
    project_id: int,
    discovery: dict,
    suggested_style: str,
    plant_selection: List[dict],
    boq: List[dict],
    total_cost: int,
    estimated_days: int,
    terms: List[str],
    model_notes: str,
    render_base64: str,
    remaining_credits: int,
) -> dict:
    return {
        "project_id": project_id,
        "summary": discovery["summary"],
        "space_type": discovery["space_type"],
        "sunlight": discovery["sunlight"],
        "soil_condition": discovery["soil_condition"],
        "area_sqft": discovery["area_sqft"],
        "suggested_style": suggested_style,
        "plant_selection": plant_selection,
        "boq": boq,
        "total_cost_inr": f"₹{total_cost:,.0f}",
        "remaining_credits": remaining_credits,
        "estimated_days": estimated_days,
        "terms": terms,
        "model_notes": model_notes,
        "render_base64": render_base64,
    }


@app.post("/api/auth/register", response_model=Token)
def register(user_create: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_email(db, user_create.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user_role = user_create.role if user_create.role in ["client", "architect"] else "client"
    user = create_user(db, user_create, role=user_role)
    access_token = create_access_token({"email": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/auth/login", response_model=Token)
def login(user_login: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, user_login.email, user_login.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    access_token = create_access_token({"email": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/users/me", response_model=UserResponse)
def read_current_user(current_user=Depends(get_current_active_user)):
    return current_user


@app.post("/api/projects", response_model=ProjectResponse)
def create_project_endpoint(project_create: ProjectCreate, current_user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    project = create_project(
        db,
        owner_id=current_user.id,
        name=project_create.name,
        area_sqft=int(project_create.area_sqft),
        preferred_style=project_create.preferred_style,
        image_filename=project_create.image_filename,
    )
    return project


@app.get("/api/projects", response_model=List[ProjectResponse])
def list_projects(current_user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    if current_user.role == "admin":
        return get_all_projects(db)
    return get_projects_for_user(db, current_user.id)


@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
def read_project(project_id: int, current_user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if project.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return project


@app.post("/api/projects/{project_id}/chat", response_model=ChatResponse)
def chat_with_project(
    project_id: int,
    chat_request: ChatRequest,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if project.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    analysis_details = project.analysis_details or {}
    context_summary = [
        f"Project name: {project.name}",
        f"Area: {project.area_sqft} sq ft",
        f"Preferred style: {project.preferred_style}",
        f"Space type: {project.space_type or analysis_details.get('space_type', 'Unknown')}",
        f"Sunlight: {project.sunlight or analysis_details.get('sunlight', 'Unknown')}",
        f"Soil condition: {project.soil_condition or analysis_details.get('soil_condition', 'Unknown')}",
        f"Summary: {project.summary or analysis_details.get('summary', 'No summary available')}",
    ]

    query = (
        f"{chat_request.message} "
        f"Project details: {'; '.join(context_summary)}"
    )
    retrieved_docs, _ = RAG_STORE.retrieve(query, top_k=6)

    prompt = (
        "You are a grounded Indian landscape assistant. Use the retrieved landscaping knowledge and the saved project context only. "
        "Answer briefly, directly, and accurately, and do not invent plants, rates, or scope items that are not present in the project data.\n\n"
        f"Project context:\n- {'\n- '.join(context_summary)}\n\n"
        f"Project analysis details:\n{json.dumps(analysis_details, ensure_ascii=False, indent=2)}\n\n"
        "Retrieved RAG context:\n"
        + "\n".join([f"- {doc['type'].title()}: {doc['text']}" for doc in retrieved_docs])
        + f"\n\nUser question: {chat_request.message}\n\n"
        "Return a concise, practical answer tied to this project and the available knowledge base."
    )

    answer = generate_chat_response(prompt)
    lower_message = chat_request.message.lower()
    if not analysis_details:
        answer = "Please run the image analysis first, then ask project questions again."
    elif any(token in lower_message for token in ["plant", "recommend", "which plant", "best plant"]):
        selected = analysis_details.get("plant_selection") or []
        if selected:
            first = selected[0]
            answer = (
                f"For this project, the highest-fit plant is {first['common_name']} ({first['botanical_name']}). "
                f"It suits {analysis_details.get('sunlight', 'the site')} exposure and the current {analysis_details.get('space_type', 'space')} context."
            )
    elif any(token in lower_message for token in ["boq", "cost", "budget", "estimate"]):
        total_cost = analysis_details.get("total_cost_inr")
        if total_cost is not None:
            answer = f"The current BOQ estimate for this project is ₹{int(total_cost):,} based on the saved analysis details."
    elif any(token in lower_message for token in ["layout", "path", "zone", "placement"]):
        answer = (
            "The saved layout guidance points to a structured planting and circulation plan for the current site. "
            f"The site is classified as {analysis_details.get('space_type', 'Unknown')} with {analysis_details.get('sunlight', 'Unknown')} sunlight and {analysis_details.get('soil_condition', 'Unknown')} soil."
        )
    elif answer.lower().startswith("i could not generate"):
        answer = (
            "Based on the saved analysis, the project has been scoped as a "
            f"{analysis_details.get('space_type', 'Unknown')} space with {analysis_details.get('sunlight', 'Unknown')} sunlight and {analysis_details.get('soil_condition', 'Unknown')} soil. "
            "The current recommendation is to keep the design aligned with the saved plant selection, BOQ, and layout blueprint."
        )

    return {"project_id": project.id, "answer": answer}


@app.post("/api/projects/{project_id}/analyze", response_model=AnalysisResponse)
async def analyze_project(
    project_id: int,
    image: UploadFile = File(...),
    area_sqft: float = Form(150.0),
    preferred_style: str = Form("Modern Indian Garden"),
    render_mode: str = Form("3d"),
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if project.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if not deduct_credits(db, current_user, ANALYSIS_CREDIT_COST):
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient credits")

    image_path = UPLOAD_DIR / image.filename
    with image_path.open("wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    discovery = analyze_image(str(image_path))
    discovery["area_sqft"] = area_sqft
    suggested_style = design_concept(discovery, preferred_style)
    seasonal_factor = choose_seasonal_factor("summer", HORTICULTURE_DATA)
    plant_candidates = search_plants(discovery, BRAIN, suggested_style)
    rag_query = (
        f"Recommend plants, structural layout and industry-standard BOQ for a {suggested_style} "
        f"{discovery['space_type']} with {discovery['sunlight']} exposure and {discovery['soil_condition']} soil."
    )
    retrieved_docs, _ = RAG_STORE.retrieve(rag_query, top_k=10)
    industry_context = build_industry_context(discovery, suggested_style, area_sqft, HORTICULTURE_DATA)
    rag_prompt = build_rag_prompt(discovery, suggested_style, plant_candidates, BRAIN, retrieved_docs) + "\n\n" + industry_context
    model_notes = describe_space(str(image_path), rag_prompt)
    plant_selection = select_plants(discovery, plant_candidates, suggested_style)
    boq, total_cost = calculate_industry_boq(area_sqft, plant_selection, HORTICULTURE_DATA, seasonal_factor)
    layout_blueprint = build_layout_blueprint(discovery, suggested_style, plant_selection, DESIGN_DATA)
    estimated_days = estimate_timeline(area_sqft, suggested_style)
    terms = generate_terms(area_sqft, suggested_style)
    requested_mode = "2d" if str(render_mode).lower() == "2d" else "3d"
    render_prompt = build_render_prompt(discovery, suggested_style, plant_selection, mode=requested_mode)
    render_base64 = generate_design_render(render_prompt)

    analysis_payload = {
        "summary": discovery["summary"],
        "space_type": discovery["space_type"],
        "sunlight": discovery["sunlight"],
        "soil_condition": discovery["soil_condition"],
        "project_id": project.id,
        "plant_selection": plant_selection,
        "boq": boq,
        "total_cost_inr": int(total_cost),
        "estimated_days": estimated_days,
        "terms": terms,
        "model_notes": model_notes,
        "render_base64": render_base64,
        "layout_blueprint": layout_blueprint,
    }

    save_project_analysis(
        db,
        project,
        summary=discovery["summary"],
        space_type=discovery["space_type"],
        sunlight=discovery["sunlight"],
        soil_condition=discovery["soil_condition"],
        total_cost_inr=int(total_cost),
        analysis_details=analysis_payload,
        status="completed",
    )

    return build_analysis_response(
        project_id=project.id,
        discovery=discovery,
        suggested_style=suggested_style,
        plant_selection=plant_selection,
        boq=boq,
        total_cost=total_cost,
        estimated_days=estimated_days,
        terms=terms,
        model_notes=model_notes,
        render_base64=render_base64,
        remaining_credits=current_user.credits,
    )


@app.post("/api/payments", response_model=PaymentResponse)
def create_payment(request: PaymentRequest, current_user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    payment = simulate_payment(request.provider, request.amount_inr)
    if payment.status in ["succeeded", "created"]:
        credit_amount = max(1, int(request.amount_inr / CREDIT_TOPUP_RATE))
        add_credits(db, current_user, credit_amount)
    return payment


@app.get("/api/admin/users", response_model=List[UserResponse])
def admin_list_users(current_user=Depends(get_current_admin_user), db: Session = Depends(get_db)):
    return get_all_users(db)


@app.get("/api/admin/projects", response_model=List[ProjectResponse])
def admin_list_projects(current_user=Depends(get_current_admin_user), db: Session = Depends(get_db)):
    return get_all_projects(db)


@app.get("/api/projects/{project_id}/proposal")
def get_project_proposal(project_id: int, current_user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if project.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if not project.analysis_details:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Proposal not available for an unanalyzed project")

    pdf_base64 = generate_pdf_proposal(project.name, project.analysis_details)
    return {"project_id": project.id, "proposal_pdf_base64": pdf_base64}
