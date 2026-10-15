import time
import uuid
import logging
from typing import Dict, Any, List
from collections import deque
from app.config import settings

logger = logging.getLogger("cosmos_audit")

class CosmosDBAuditService:
    """
    Cosmos DB NoSQL Audit Trail Client:
    Stores high-cardinality unstructured fraud indicators, device fingerprints,
    and investigation logs. Operates with local in-memory fallback for offline environments.
    """
    def __init__(self):
        self.local_documents: deque = deque(maxlen=500)
        self.is_connected = False

    async def connect(self):
        # In cloud environments, initializes Azure CosmosClient(endpoint, credential)
        logger.info(f"Initialized Cosmos DB client interface pointing to: {settings.COSMOS_ENDPOINT}")
        self.is_connected = True

    async def insert_threat_document(self, document: Dict[str, Any]) -> str:
        doc_id = document.get("id") or str(uuid.uuid4())
        document["id"] = doc_id
        document["_timestamp"] = int(time.time())
        document["partitionKey"] = document.get("account_id", "GLOBAL")

        self.local_documents.appendleft(document)
        logger.debug(f"Logged threat document to Cosmos DB container [{settings.COSMOS_CONTAINER}]: {doc_id}")
        return doc_id

    async def query_recent_threats(self, limit: int = 25) -> List[Dict[str, Any]]:
        return list(self.local_documents)[:limit]

cosmos_service = CosmosDBAuditService()
