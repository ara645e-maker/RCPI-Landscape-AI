import importlib
import traceback
import sys
sys.path.insert(0, '.')
modules = [
    'backend.auth',
    'backend.crud',
    'backend.database',
    'backend.dependencies',
    'backend.models',
    'backend.image_analyzer',
    'backend.llm_client',
    'backend.stable_diffusion',
    'backend.rag_store',
    'backend.industry_engine',
    'backend.brain',
    'backend.main',
]
errors = []
for m in modules:
    try:
        importlib.import_module(m)
    except Exception as exc:
        errors.append((m, traceback.format_exception_only(type(exc), exc)[-1].strip()))
print(errors)
