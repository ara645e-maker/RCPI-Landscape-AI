from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str
    role: Optional[str] = "client"


class UserResponse(UserBase):
    id: int
    role: str
    credits: int
    is_active: bool
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "protected_namespaces": (),
    }


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class BOQItem(BaseModel):
    item: str
    quantity: str
    unit_cost_inr: str
    total_cost_inr: str


class PlantSelection(BaseModel):
    botanical_name: str
    common_name: str
    hindi_name: str
    sunlight: List[str]
    water: str
    height_m: float | str
    growth: str
    maintenance: str
    placement: List[str]
    reason: str


class AnalysisResponse(BaseModel):
    project_id: int
    summary: str
    space_type: str
    sunlight: str
    soil_condition: str
    area_sqft: float
    suggested_style: str
    plant_selection: List[PlantSelection]
    boq: List[BOQItem]
    total_cost_inr: str
    remaining_credits: int
    estimated_days: int
    terms: List[str]
    model_notes: str
    render_base64: str

    model_config = {
        "from_attributes": True,
        "protected_namespaces": (),
    }


class ProjectCreate(BaseModel):
    name: Optional[str] = "Landscape Project"
    area_sqft: float
    preferred_style: str
    image_filename: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    area_sqft: float
    preferred_style: str
    space_type: Optional[str] = None
    sunlight: Optional[str] = None
    soil_condition: Optional[str] = None
    total_cost_inr: Optional[int] = None
    status: str
    analysis_details: Optional[dict] = None
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "protected_namespaces": (),
    }


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    project_id: int
    answer: str


class PaymentRequest(BaseModel):
    amount_inr: int
    provider: str


class PaymentResponse(BaseModel):
    provider: str
    amount_inr: int
    currency: str
    reference_id: Optional[str] = None
    status: str
    metadata: Optional[dict] = None
