import pytest
import os
import sys

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services.redis_service import redis_service
from app.services.database_service import db_service
from app.services.rabbitmq_service import rabbitmq_service
from app.services.cosmos_service import cosmos_service

@pytest.fixture(autouse=True)
async def setup_test_services():
    await db_service.connect()
    await redis_service.connect()
    await rabbitmq_service.connect()
    await cosmos_service.connect()
    yield
    await rabbitmq_service.close()
    await redis_service.close()
    await db_service.close()
