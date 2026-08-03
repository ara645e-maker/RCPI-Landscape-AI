import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'saas.db'}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db() -> None:
    from backend import models
    from backend.auth import get_password_hash

    Base.metadata.create_all(bind=engine)
    if os.environ.get("DEFAULT_ADMIN_EMAIL") and os.environ.get("DEFAULT_ADMIN_PASSWORD"):
        with SessionLocal() as session:
            admin_email = os.environ.get("DEFAULT_ADMIN_EMAIL")
            admin = session.query(models.User).filter(models.User.email == admin_email).first()
            if not admin:
                admin = models.User(
                    email=admin_email,
                    full_name=os.environ.get("DEFAULT_ADMIN_NAME", "Admin"),
                    hashed_password=get_password_hash(os.environ.get("DEFAULT_ADMIN_PASSWORD")),
                    role="admin",
                    credits=100,
                )
                session.add(admin)
                session.commit()
