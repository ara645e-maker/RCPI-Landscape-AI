import json
from pathlib import Path
from typing import List

import numpy as np

from backend import embeddings as embeddings_module


class RAGStore:
    def __init__(self, kb_paths: List[Path], cache_path: Path):
        self.kb_paths = [Path(path) for path in kb_paths]
        self.cache_path = Path(cache_path)
        self.documents = []
        self.embeddings = None
        self._build_documents()
        self._load_or_build_embeddings()

    def _load_kb(self, path: Path):
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _build_documents(self):
        self.documents = []
        for path in self.kb_paths:
            kb = self._load_kb(path)
            if "flora" in kb:
                self._append_plant_documents(kb)
            if "execution_workflow" in kb or "pricing_rules" in kb:
                self._append_industry_documents(kb)
            if "zoning" in kb or "styles" in kb:
                self._append_design_documents(kb)

    def _append_plant_documents(self, kb):
        for plant in kb.get("flora", []):
            plant_text = (
                f"{plant['common_name']} ({plant['botanical_name']}), Hindi: {plant['hindi_name']}. "
                f"Regions: {', '.join(plant.get('region', []))}. Climate: {', '.join(plant.get('climate_zones', []))}. "
                f"Sunlight: {', '.join(plant.get('sunlight', []))}. Water: {plant.get('water')}. Soil: {', '.join(plant.get('soil_type', []))}. "
                f"Placement: {', '.join(plant.get('placement', []))}. Growth: {plant.get('growth')}. Bloom: {plant.get('bloom_seasons')}. "
                f"Maintenance: {plant.get('maintenance')}. Description: {plant.get('description')}"
            )
            self.documents.append({"id": plant["botanical_name"], "type": "plant", "text": plant_text, "meta": plant})

        for entry in kb.get("cost_rules", []):
            cost_text = f"{entry['name']}: ₹{entry['value_inr']}. {entry['details']}"
            self.documents.append({"id": entry["name"], "type": "cost", "text": cost_text, "meta": entry})

        for entry in kb.get("labor_rules", []):
            labor_text = f"{entry['name']}: {entry.get('value', entry.get('value_inr'))}. {entry['details']}"
            self.documents.append({"id": entry["name"], "type": "labor", "text": labor_text, "meta": entry})

    def _append_industry_documents(self, kb):
        workflow_text = " -> ".join([step["step"] for step in kb.get("execution_workflow", [])])
        self.documents.append({
            "id": "industry_workflow",
            "type": "industry",
            "text": f"Execution workflow: {workflow_text}.",
            "meta": kb.get("execution_workflow", []),
        })

        models_text = ", ".join([f"{k}: {v}" for k, v in kb.get("contract_models", {}).items()])
        self.documents.append({
            "id": "contract_models",
            "type": "industry",
            "text": f"Contracting models: {models_text}.",
            "meta": kb.get("contract_models", {}),
        })

        pricing_text = ", ".join([f"{k}: {v}" for k, v in kb.get("pricing_rules", {}).items()])
        self.documents.append({
            "id": "pricing_rules",
            "type": "industry",
            "text": f"Pricing rules: {pricing_text}.",
            "meta": kb.get("pricing_rules", {}),
        })

        nursery_text = "; ".join([f"{hub['name']} ({hub['region']}) - {hub['specialty']}" for hub in kb.get("nursery_hubs", [])])
        self.documents.append({
            "id": "nursery_hubs",
            "type": "industry",
            "text": f"Nursery hubs: {nursery_text}.",
            "meta": kb.get("nursery_hubs", []),
        })

        self.documents.append({
            "id": "deal_terms",
            "type": "industry",
            "text": f"Deal terms: {'; '.join(kb.get('deal_terms', []))}",
            "meta": kb.get("deal_terms", []),
        })

        self.documents.append({
            "id": "procurement_logic",
            "type": "industry",
            "text": kb.get("procurement_logic", ""),
            "meta": kb.get("procurement_logic", ""),
        })

    def _append_design_documents(self, kb):
        zoning_text = "; ".join([f"{zone['zone']} {zone['ratio']}" for zone in kb.get("zoning", [])])
        self.documents.append({
            "id": "zoning",
            "type": "design",
            "text": f"Zoning ratios: {zoning_text}.",
            "meta": kb.get("zoning", []),
        })

        style_text = "; ".join([f"{name}: {data.get('palette', '')}" for name, data in kb.get("styles", {}).items()])
        self.documents.append({
            "id": "style_guidelines",
            "type": "design",
            "text": f"Style guidelines: {style_text}.",
            "meta": kb.get("styles", {}),
        })

        self.documents.append({
            "id": "planting_layers",
            "type": "design",
            "text": f"Planting layers: {', '.join(kb.get('planting_layers', []))}.",
            "meta": kb.get("planting_layers", []),
        })

        color_text = "; ".join([f"{p['name']}: {p['notes']}" for p in kb.get("color_palettes", [])])
        self.documents.append({
            "id": "color_palettes",
            "type": "design",
            "text": f"Color palettes: {color_text}.",
            "meta": kb.get("color_palettes", []),
        })

        self.documents.append({
            "id": "layout_rules",
            "type": "design",
            "text": f"Layout rules: {'; '.join([rule['rule'] for rule in kb.get('layout_rules', [])])}",
            "meta": kb.get("layout_rules", []),
        })

        self.documents.append({
            "id": "pairing_formulas",
            "type": "design",
            "text": "; ".join([f"{entry['primary']} with {entry['underplant']} and {entry['accent']}" for entry in kb.get('pairing_formulas', [])]),
            "meta": kb.get("pairing_formulas", []),
        })

    def _load_or_build_embeddings(self):
        try:
            if self.cache_path.exists():
                self.embeddings = embeddings_module.load_embeddings(self.cache_path)
            else:
                texts = [doc["text"] for doc in self.documents]
                self.embeddings = embeddings_module.embed_texts(texts)
                embeddings_module.save_embeddings(self.cache_path, self.embeddings)
        except Exception:
            self.embeddings = self._build_fallback_embeddings()

    def _build_fallback_embeddings(self):
        vectors = []
        vocabulary = {}
        for doc in self.documents:
            vector = np.zeros(512, dtype=np.float32)
            for token in doc["text"].lower().split():
                idx = vocabulary.setdefault(token, len(vocabulary) % 512)
                vector[idx] += 1.0
            norm = np.linalg.norm(vector)
            vectors.append(vector / norm if norm > 0 else vector)
        return np.vstack(vectors) if vectors else np.zeros((0, 512), dtype=np.float32)

    def _coerce_query_embedding(self, query_embedding):
        if self.embeddings is None or len(self.embeddings) == 0:
            return None

        embedding_dim = int(self.embeddings.shape[1])
        embedding = np.asarray(query_embedding, dtype=np.float32).reshape(-1)
        if embedding.size == 0:
            return np.zeros(embedding_dim, dtype=np.float32)

        if embedding.size != embedding_dim:
            if embedding.size < embedding_dim:
                padded = np.zeros(embedding_dim, dtype=np.float32)
                padded[:embedding.size] = embedding
                return padded
            return embedding[:embedding_dim]

        return embedding

    def retrieve(self, query: str, top_k: int = 10):
        if not self.documents:
            return [], []

        try:
            query_embedding = embeddings_module.embed_texts([query])[0]
        except Exception:
            if self.embeddings is None or len(self.embeddings) == 0:
                return [], []
            query_vector = np.zeros(self.embeddings.shape[1], dtype=np.float32)
            for token in query.lower().split():
                query_vector[hash(token) % self.embeddings.shape[1]] += 1.0
            norm = np.linalg.norm(query_vector)
            query_embedding = query_vector / norm if norm > 0 else query_vector

        if self.embeddings is None or len(self.embeddings) == 0:
            return self.documents[:top_k], [0.0] * min(top_k, len(self.documents))

        query_embedding = self._coerce_query_embedding(query_embedding)
        scores = np.dot(self.embeddings, query_embedding)
        top_indices = np.argsort(scores)[::-1][:top_k]
        valid_indices = [int(i) for i in top_indices if 0 <= int(i) < len(self.documents)]
        if not valid_indices:
            return [self.documents[0]] if self.documents else [], [0.0]
        valid_indices = valid_indices[: min(len(valid_indices), len(self.documents))]
        return [self.documents[i] for i in valid_indices], [float(scores[i]) for i in valid_indices]
