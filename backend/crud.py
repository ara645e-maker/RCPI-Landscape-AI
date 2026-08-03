from sqlalchemy.orm import Session

from backend import models
from backend.auth import verify_password, get_password_hash
from backend.schemas import UserCreate


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user_create: UserCreate, role: str = "client"):
    hashed_password = get_password_hash(user_create.password)
    user = models.User(
        email=user_create.email,
        full_name=user_create.full_name,
        hashed_password=hashed_password,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def get_project(db: Session, project_id: int):
    return db.query(models.Project).filter(models.Project.id == project_id).first()


def get_projects_for_user(db: Session, user_id: int):
    return db.query(models.Project).filter(models.Project.owner_id == user_id).order_by(models.Project.created_at.desc()).all()


def get_all_projects(db: Session):
    return db.query(models.Project).order_by(models.Project.created_at.desc()).all()


def create_project(db: Session, owner_id: int, name: str, area_sqft: int, preferred_style: str, image_filename: str | None = None):
    project = models.Project(
        owner_id=owner_id,
        name=name,
        image_filename=image_filename,
        area_sqft=area_sqft,
        preferred_style=preferred_style,
        status="pending",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def save_project_analysis(db: Session, project: models.Project, summary: str, space_type: str, sunlight: str, soil_condition: str, total_cost_inr: int, analysis_details: dict | None = None, status: str = "completed"):
    project.summary = summary
    project.space_type = space_type
    project.sunlight = sunlight
    project.soil_condition = soil_condition
    project.total_cost_inr = total_cost_inr
    project.analysis_details = analysis_details
    project.status = status
    db.commit()
    db.refresh(project)
    return project


def deduct_credits(db: Session, user: models.User, amount: int):
    if user.credits < amount:
        return False
    user.credits -= amount
    db.commit()
    db.refresh(user)
    return True


def add_credits(db: Session, user: models.User, amount: int):
    user.credits += amount
    db.commit()
    db.refresh(user)
    return user


def get_all_users(db: Session):
    return db.query(models.User).order_by(models.User.created_at.desc()).all()
