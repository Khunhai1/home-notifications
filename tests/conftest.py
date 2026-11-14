import os
import uuid

import pytest

from homenotif import db
from homenotif.migrate import migrate

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@pytest.fixture
def conn():
    """A connection to TEST_DATABASE_URL inside a throwaway schema with the migrations applied."""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set")
    schema = f"test_{uuid.uuid4().hex[:12]}"
    with db.connect(url) as c:
        c.execute(f"CREATE SCHEMA {schema}")
        c.execute(f"SET search_path TO {schema}")
        try:
            migrate(c)
            yield c
        finally:
            c.execute(f"DROP SCHEMA {schema} CASCADE")
