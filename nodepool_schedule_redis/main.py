import os
import json
import redis
from google.cloud import firestore
import structlog
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.config_loader import load_config
load_config()

logger = structlog.get_logger()

r = redis.Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), db=0, decode_responses=True)
REDIS_SCHEDULER_SET = "gke:scheduler"
REDIS_PREFIX = "gke_nodepool_schedule:"

logger = structlog.get_logger()
firestore_client = firestore.Client()
COLLECTION_NAME = "gke-nodepool-scheduler"
REDIS_KEY_PREFIX = "gke_nodepool_schedule"

def main():
    collection_ref = firestore_client.collection(COLLECTION_NAME)
    docs = collection_ref.stream()
    try:
        logger.info("Syncing Firestore data to Redis", collection=COLLECTION_NAME)
        for doc in docs:
            doc_id = doc.id
            data = doc.to_dict()
            redis_key = f"gke_nodepool_schedule:{doc_id}"
            # Store each nodepool document individually in Redis
            logger.info("Storing data in Redis", redis_key=redis_key, data=data)
            r.set(redis_key, json.dumps(data))
            # Add the key reference to a Redis Set for index
            r.sadd("gke:scheduler", redis_key)
        logger.info("Firestore data synced to Redis", collection=COLLECTION_NAME)
    except Exception as e:
        logger.error("Error syncing Firestore to Redis", error=str(e))
        raise Exception(f"Failed to sync Firestore to Redis: {e}")

if __name__ == "__main__":
    main()
