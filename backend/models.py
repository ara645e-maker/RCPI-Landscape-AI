from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(256), unique=True, index=True, nullable=False)
    full_name = Column(String(256), nullable=True)
    hashed_password = Column(String(512), nullable=False)
    role = Column(String(50), default="client", nullable=False)
    credits = Column(Integer, default=20, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    projects = relationship("Project", back_populates="owner")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(256), nullable=False)
    image_filename = Column(String(512), nullable=True)
    area_sqft = Column(Integer, nullable=False)
    preferred_style = Column(String(128), nullable=False)
    summary = Column(Text, nullable=True)
    space_type = Column(String(128), nullable=True)
    sunlight = Column(String(128), nullable=True)
    soil_condition = Column(String(128), nullable=True)
    total_cost_inr = Column(Integer, nullable=True)
    status = Column(String(64), default="draft", nullable=False)
    analysis_details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="projects")
