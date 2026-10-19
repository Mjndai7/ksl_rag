import os
import sys
from pathlib import Path

# Settings require these; unit tests never connect to the real services.
os.environ.setdefault("POSTGRES_URL", "postgresql://test:test@127.0.0.1:1/test")
os.environ.setdefault("NEO4J_PASSWORD", "test")
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
