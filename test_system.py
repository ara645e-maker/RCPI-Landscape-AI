import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import backend.embeddings as embeddings_module

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.auth import create_access_token, verify_password
from backend.crud import create_project, create_user, get_project, save_project_analysis
from backend.database import Base, SessionLocal, engine
from backend.main import app
import importlib
import backend.proposal as proposal_module
import backend.rag_store as rag_store_module
from backend.proposal import generate_pdf_proposal
from backend.rag_store import RAGStore
from backend.industry_engine import calculate_industry_boq, build_layout_blueprint, choose_seasonal_factor
from backend.brain import build_rag_prompt, build_render_prompt, design_concept, search_plants, select_plants, estimate_timeline, generate_terms
from backend.llm_client import generate_chat_response
from backend.image_analyzer import analyze_image
from backend.schemas import UserCreate
from fastapi.testclient import TestClient


class _FastPath:
    @staticmethod
    def patch_env():
        embedding_dim = 384
        embeddings_module.get_embedding_model = lambda: None
        embeddings_module.embed_texts = lambda texts: np.zeros((len(texts), embedding_dim), dtype=np.float32)
        embeddings_module.load_embeddings = lambda path: np.zeros((0, embedding_dim), dtype=np.float32)
        embeddings_module.save_embeddings = lambda path, embeddings: None


_FastPath.patch_env()

proposal_module.generate_pdf_proposal = generate_pdf_proposal
rag_store_module.RAGStore = RAGStore


class SystemIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        for table in reversed(Base.metadata.sorted_tables):
            self.db.execute(table.delete())
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _create_user(self, email="test@example.com", password="secret123", role="client"):
        user_create = UserCreate(email=email, full_name="Test User", password=password, role=role)
        user = create_user(self.db, user_create, role=role)
        return user

    def test_auth_and_project_flow(self):
        user = self._create_user()
        token = create_access_token({"email": user.email, "role": user.role})
        headers = {"Authorization": f"Bearer {token}"}

        register_resp = self.client.post(
            "/api/auth/register",
            json={"email": "new@example.com", "full_name": "New User", "password": "secret123", "role": "client"},
        )
        self.assertIn(register_resp.status_code, {200, 400})

        login_resp = self.client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "secret123"},
        )
        self.assertEqual(login_resp.status_code, 200)
        self.assertIn("access_token", login_resp.json())

        project_resp = self.client.post(
            "/api/projects",
            json={"name": "Demo Project", "area_sqft": 180, "preferred_style": "Modern Indian Garden"},
            headers=headers,
        )
        self.assertEqual(project_resp.status_code, 200)
        project_id = project_resp.json()["id"]

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(b"\x89PNG\r\n\x1a\n")
            image_path = tmp.name

        with open(image_path, "rb") as fh:
            analyze_resp = self.client.post(
                f"/api/projects/{project_id}/analyze",
                files={"image": ("sample.png", fh, "image/png")},
                data={"area_sqft": 180, "preferred_style": "Modern Indian Garden"},
                headers=headers,
            )

        self.assertIn(analyze_resp.status_code, {200, 402})
        if analyze_resp.status_code == 200:
            body = analyze_resp.json()
            self.assertIn("plant_selection", body)
            self.assertIn("boq", body)
            self.assertIn("render_base64", body)

        project = get_project(self.db, project_id)
        self.assertIsNotNone(project)

        chat_resp = self.client.post(
            f"/api/projects/{project_id}/chat",
            json={"message": "Which plant should I prioritize for this balcony?"},
            headers=headers,
        )
        self.assertEqual(chat_resp.status_code, 200)
        self.assertIn("answer", chat_resp.json())

        os.remove(image_path)

    def test_rag_and_boq_pipeline(self):
        brain = {
            "flora": [
                {
                    "common_name": "Rosemary",
                    "botanical_name": "Rosmarinus officinalis",
                    "hindi_name": "रोज़मेरी",
                    "sunlight": ["Full Sun"],
                    "water": "Low",
                    "height_m": 1.0,
                    "growth": "Moderate",
                    "maintenance": "Low",
                    "placement": ["Balcony", "Rooftop"],
                    "description": "A hardy aromatic shrub ideal for sunny Indian balconies.",
                }
            ],
            "cpwd_rates": {
                "plant_unit_cost": 90,
                "soil_per_cuft": 120,
                "fertilizer_per_kg": 60,
                "turf_per_sqft": 30,
                "labor_per_sqft": 25,
                "irrigation_per_sqft": 18,
            },
        }
        discovery = {"space_type": "Balcony", "sunlight": "Full Sun", "soil_condition": "Dry"}
        style = design_concept(discovery, "Modern Indian Garden")
        plant_candidates = search_plants(discovery, brain, style, top_n=3)
        selected = select_plants(discovery, plant_candidates, style)
        self.assertTrue(selected)

        rag_store = RAGStore([Path("backend/data/indian_landscape_rag.json")], Path("backend/data/rag_embeddings.npy"))
        docs, _ = rag_store.retrieve("balcony garden plants", top_k=5)
        self.assertTrue(docs)

        rag_prompt = build_rag_prompt(discovery, style, selected, brain, docs)
        self.assertIn("Plant knowledge base", rag_prompt)

        render_prompt_2d = build_render_prompt(discovery, style, selected, mode="2d")
        self.assertIn("blueprint", render_prompt_2d.lower())

        render_prompt_3d = build_render_prompt(discovery, style, selected, mode="3d")
        self.assertIn("photorealistic", render_prompt_3d.lower())

        chat_answer = generate_chat_response("Answer with a short, grounded recommendation for this balcony garden.")
        self.assertIsInstance(chat_answer, str)
        self.assertTrue(chat_answer)

        seasonal_factor = choose_seasonal_factor("summer", {"pricing_rules": {"seasonal_variations": {"summer": 1.1}}})
        self.assertGreater(seasonal_factor, 1.0)

        boq, total_cost = calculate_industry_boq(200, selected, {"pricing_rules": {"cleanup_per_sqft": 4, "soil_per_cuft": 120, "soil_wastage_pct": 10, "turf_wastage_pct": 10, "turf_per_sqft": 30, "hardscape_per_sqft": 20, "drainage_per_sqft": 8, "irrigation_per_sqft": 15, "labor_per_sqft": 25, "contingency_pct": 5}}, seasonal_factor)
        self.assertGreater(total_cost, 0)
        self.assertTrue(boq)

        blueprint = build_layout_blueprint(discovery, style, selected, {"styles": {style: {"palette": "warm terracotta"}}, "planting_layers": ["ground", "middle", "canopy"], "zoning": ["public", "private"], "layout_rules": [{"rule": "Maintain clear pathways."}]})
        self.assertIn("guidance", blueprint)

        estimated_days = estimate_timeline(200, style)
        terms = generate_terms(200, style)
        self.assertGreater(estimated_days, 0)
        self.assertTrue(terms)

    def test_pdf_generation_and_image_analysis(self):
        analysis = {
            "summary": "Sample landscape proposal",
            "space_type": "Balcony",
            "sunlight": "Full Sun",
            "soil_condition": "Dry",
            "area_sqft": 150,
            "plant_selection": [{"common_name": "Rosemary", "botanical_name": "Rosmarinus officinalis", "reason": "Great for sunny balcony"}],
            "boq": [{"item": "Planting", "quantity": "5 nos", "unit_cost_inr": "₹90", "total_cost_inr": "₹450"}],
            "terms": ["Payment due on delivery"],
        }
        pdf_b64 = generate_pdf_proposal("Demo Proposal", analysis)
        self.assertTrue(pdf_b64)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(b"\x89PNG\r\n\x1a\n")
            image_path = tmp.name

        result = analyze_image(image_path)
        self.assertIn("space_type", result)
        self.assertIn("sunlight", result)
        os.remove(image_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
