import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./phase2-test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-longer-than-thirty-two-characters")
