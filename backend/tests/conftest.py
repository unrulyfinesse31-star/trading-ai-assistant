import os

os.environ.setdefault("JWT_SECRET", "a-very-long-development-secret-key-123456")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest

pytest_plugins = ["pytest_asyncio"]
