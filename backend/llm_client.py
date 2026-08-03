import os
import shutil
import subprocess
from pathlib import Path

MODEL = os.environ.get("OLLAMA_MODEL", "llava")
TEXT_MODEL = os.environ.get("OLLAMA_TEXT_MODEL", "llama3.2")
OLLAMA = os.environ.get("OLLAMA_CMD", "ollama")
HF_VISION_MODEL = os.environ.get("HF_VISION_MODEL", "nlpconnect/vit-gpt2-image-captioning")
HF_TEXT_MODEL = os.environ.get("HF_TEXT_MODEL", "google/flan-t5-small")


def _has_torch() -> bool:
    try:
        import torch
        return True
    except ImportError:
        return False


def _import_torch():
    try:
        import torch
        return torch
    except ImportError as exc:
        raise ImportError("torch is required for local vision fallback") from exc


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def hf_image_caption(image_path: str) -> str:
    try:
        from transformers import pipeline
        torch = _import_torch()

        device = 0 if torch.cuda.is_available() else -1
        pipe = pipeline("image-to-text", model=HF_VISION_MODEL, device=device)
        output = pipe(image_path, max_new_tokens=80)
        if isinstance(output, list) and output:
            return output[0].get("generated_text", "")
        return ""
    except Exception:
        return ""


def hf_text_completion(prompt: str) -> str:
    try:
        from transformers import pipeline
        torch = _import_torch()

        device = 0 if torch.cuda.is_available() else -1
        pipe = pipeline("text2text-generation", model=HF_TEXT_MODEL, device=device)
        output = pipe(prompt, max_new_tokens=180, do_sample=False)
        if isinstance(output, list) and output:
            return output[0].get("generated_text", "").strip()
        return ""
    except Exception:
        return ""


def generate_chat_response(prompt: str) -> str:
    model_prompt = prompt.strip()
    if command_exists(OLLAMA):
        try:
            cmd = [OLLAMA, "run", TEXT_MODEL, "--no-stream", "--prompt", model_prompt]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            if result.returncode == 0 and result.stdout:
                return result.stdout.strip()
        except Exception:
            pass

    completion = hf_text_completion(model_prompt)
    if completion:
        return completion

    return "I could not generate a grounded answer from the local model. Please verify that the project context has been analyzed first."


def describe_space(image_path: str, prompt: str) -> str:
    model_prompt = prompt.strip()
    if command_exists(OLLAMA):
        try:
            cmd = [OLLAMA, "run", MODEL, "--no-stream", "--prompt", model_prompt, "--image", image_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            if result.returncode == 0 and result.stdout:
                return result.stdout.strip()
        except Exception:
            pass

    caption = hf_image_caption(image_path)
    if caption:
        model_prompt = f"{model_prompt}\n\nImage caption:\n{caption}"

    completion = hf_text_completion(model_prompt)
    if completion:
        return completion

    return caption or "Local vision model could not analyze image. Using default Indian landscape assumptions."
