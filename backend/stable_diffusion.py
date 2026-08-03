import base64
import os
from io import BytesIO

MODEL_ID = os.environ.get("SD_MODEL_ID", "runwayml/stable-diffusion-v1-5")

_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        try:
            import torch
            from diffusers import StableDiffusionPipeline
        except ImportError as exc:
            raise ImportError("torch and diffusers are required for Stable Diffusion") from exc
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _pipeline = StableDiffusionPipeline.from_pretrained(MODEL_ID, torch_dtype=torch.float16 if device == "cuda" else torch.float32)
        _pipeline = _pipeline.to(device)
    return _pipeline


def generate_design_render(prompt: str, width: int = 768, height: int = 512) -> str:
    try:
        pipe = get_pipeline()
        image = pipe(prompt, height=height, width=width, num_inference_steps=25).images[0]
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception:
        return ""
