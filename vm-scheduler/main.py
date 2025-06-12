import pytz
from datetime import datetime
from google.auth import default
import structlog
import json
import os 
import sys
import requests
import redis
from googleapiclient.discovery import build
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.config_loader import load_config

load_config()
logger = structlog.get_logger()
r = redis.Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), db=0, decode_responses=True)
REDIS_SCHEDULER_SET = "vm:scheduler"
REDIS_PREFIX = "vm_schedule:"

vmops_api = os.getenv("API_ENDPOINT") + "/vm-operation"
credentials, _ = default()
compute = build("compute", "v1", credentials=credentials)

def get_vm_status(project_id, zone, instance_name):
    try:
        instance = compute.instances().get(
            project=project_id,
            zone=zone,
            instance=instance_name
        ).execute()
        return instance["status"]  # e.g., "RUNNING", "TERMINATED"
    except Exception as e:
        logger.error("Failed to get VM status", vm=instance_name, error=str(e))
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

def trigger_vm_action(data, action):
    try:
        payload = {
                "project_id": data["project_id"],
                "zone": data["zone"],
                "vm_name": data["vm_name"],
                "action": action
            }
        response = requests.post(vmops_api, json=payload)
        logger.info("Response status", status=response.status_code)
        return {"data": response.json(), "status": response.status_code}
    except Exception as e:
        logger.error("Failed to trigger VM action", vm=data["vm_name"], action=action, error=str(e))
        return False
        
def main():
    keys = r.smembers(REDIS_SCHEDULER_SET)
    for key in keys:
        #key = raw_key.decode("utf-8")
        logger.info(f"Processing key: {key}")
        data_json = r.get(key)
        if not data_json:
            continue
        data = json.loads(data_json)
        in_business = is_business_hour(data["business_hours"])
        desired_action = "start" if in_business else "stop"
        status = get_vm_status(data["project_id"], data["zone"], data["vm_name"])
        logger.info(f"VM {data['vm_name']} Project {data['project_id']} is in business hours: {in_business}, current status: {status} action: {desired_action}")
        
        if status is None:
            continue  # Skip if status couldn't be retrieved

        if desired_action == "start" and status != "RUNNING":
            logger.info(f"Triggering start action for VM: {data['vm_name']}")
            output=trigger_vm_action(data, "start")
            logger.info(f"Start action triggered for VM: {data['vm_name']}, http_status: {output['status']} info: {output['data']}")
        elif desired_action == "stop" and status == "RUNNING":
            output=trigger_vm_action(data, "stop")
            logger.info(f"Stop action triggered for VM: {data['vm_name']}, http_status: {output['status']} info: {output['data']}")
        else:
            logger.info(f"No action needed for VM: {data['vm_name']}")

if __name__ == "__main__":
    main()