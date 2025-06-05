import redis
import json
import requests
from datetime import datetime, time
import pytz
import structlog
from google.cloud import container_v1

logger = structlog.get_logger()

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_SCHEDULER_SET = "gke:scheduler"
REDIS_PREFIX = "gke_nodepool_schedule:"

API_ENDPOINT = "http://127.0.0.1:8080/nodepool-resize"

def get_current_nodepool_config(project_id, zone, cluster_id, nodepool_id):
    try:
        client = container_v1.ClusterManagerClient()
        nodepool_path = f"projects/{project_id}/locations/{zone}/clusters/{cluster_id}/nodePools/{nodepool_id}"
        nodepool = client.get_node_pool(name=nodepool_path)

        autoscaling = nodepool.autoscaling
        current_config = {
            "min_nodes": autoscaling.min_node_count if autoscaling else -1,
            "max_nodes": autoscaling.max_node_count if autoscaling else -1,
            "desired_node_count": nodepool.initial_node_count,
            "enable_autoscaling": autoscaling.enabled if autoscaling else False
        }

        return current_config

    except Exception as e:
        logger.error("Error fetching current nodepool config", error=str(e))
        return None
    
def is_business_hour(business_hours):
    tz = pytz.timezone("Asia/Singapore")  # adjust if needed
    now = datetime.now(tz)
    weekday = now.isoweekday()  # Monday=1 ... Sunday=7

    if weekday not in business_hours["days"]:
        return False

    start = datetime.strptime(business_hours["starttime"], "%H:%M:%S").time()
    end = datetime.strptime(business_hours["endtime"], "%H:%M:%S").time()
    logger.info(f"Current time: {now.time()}, Start: {start}, End: {end}, Weekday: {weekday}")  
    return start <= now.time() <= end

def parse_config(config_str):
    min_n, max_n, desired_n = map(int, config_str.split(","))
    return min_n, max_n, desired_n

def check_and_resize(redis_client):
    keys = redis_client.smembers(REDIS_SCHEDULER_SET)
    for raw_key in keys:
        key = raw_key.decode("utf-8")
        data_json = redis_client.get(key)
        if not data_json:
            continue
        data = json.loads(data_json)

        in_business = is_business_hour(data["business_hours"])
        config_str = data["business_hours_config"] if in_business else data["off_hours_config"]
        min_n, max_n, desired_n = parse_config(config_str)

        # Simulate existing nodepool config (in real use, query actual GKE config here)
        current_config = {
            "min_nodes": -1,
            "max_nodes": -1,
            "desired_node_count": -1,
            "enable_autoscaling": not in_business  # just for demo
        }

        # Only trigger if config is different
        logger.info(f"Checking nodepool: {data['nodepool_id']} - Business Hours: {in_business}")
        logger.info(f"Current config: {current_config}, New config: min={min_n}, max={max_n}, desired={desired_n}")
        if (
            current_config["min_nodes"] != min_n or
            current_config["max_nodes"] != max_n or
            current_config["desired_node_count"] != desired_n or
            current_config["enable_autoscaling"] != data["enable_autoscaling"]
        ):
            payload = {
                "project_id": data["project_id"],
                "zone": data["zone"],
                "cluster_id": data["cluster_id"],
                "nodepool_id": data["nodepool_id"],
                "enable_autoscaling": data["enable_autoscaling"],
                "min_nodes": min_n,
                "max_nodes": max_n,
                "desired_node_count": desired_n
            }


            logger.info(f"Triggering resize for: {data['nodepool_id']} endpoint: {API_ENDPOINT}", payload=payload)
            response = requests.post(API_ENDPOINT, json=payload)
            print(f"Response: {response.status_code} - {response.text}")

if __name__ == "__main__":
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)
    check_and_resize(r)
