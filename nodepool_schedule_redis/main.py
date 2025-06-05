import os
import json
import redis
from google.cloud import firestore
import structlog

logger = structlog.get_logger()
r = redis.Redis(host='localhost', port=6379, db=0)
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
