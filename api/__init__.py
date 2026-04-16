"""API package — aliases to backend/ for Python imports.

The backend was renamed from api/ to backend/ for Vercel compatibility,
but all Python code still uses `from api.xxx import ...`.
This __init__.py makes `import api.core` resolve to `backend/core/`.
"""
import importlib
import sys
from pathlib import Path

# Set __path__ to include backend directory so sub-imports resolve
_backend_dir = str(Path(__file__).resolve().parent.parent / "backend")
__path__ = [_backend_dir]
