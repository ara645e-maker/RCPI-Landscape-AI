import py_compile
from pathlib import Path

errors = []
for path in Path('backend').glob('*.py'):
    try:
        py_compile.compile(str(path), doraise=True)
    except Exception as exc:
        errors.append((str(path), repr(exc)))

print(errors)
