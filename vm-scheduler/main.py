import pytz
from datetime import datetime
from googleapiclient.discovery import build
from google.auth import default
import structlog
import requests

logger = structlog.get_logger()
vmops_api = "http://localhost:8080/vm-operation"
credentials, _ = default()

def parse_schedule_label(label_value):
    try:
        day_str, start, end, tz = label_value.split("-")
        days = [] if day_str == "none" else [int(d) for d in day_str.split("_")]
        return days, start, end, tz
    except Exception as e:
        logger.error(f"Error parsing label: {label_value}", error=str(e))
        raise ValueError(f"Invalid label format: {label_value}")

def is_within_schedule(days, start_time, end_time, timezone_str):
    """Check if the current time is within the specified schedule."""
    try:
        tz = pytz.timezone(timezone_str)
    except:
        tz = pytz.timezone("Asia/Singapore")  # fallback

    now = datetime.now(tz)
    weekday = now.isoweekday()  # 1 (Mon) to 7 (Sun)
    current_time = now.strftime("%H%M%S")

    if weekday not in days:
        return False

    return start_time <= current_time <= end_time

def manage_vm(compute, instance, project, zone, should_run):
    result = compute.instances().get(project=project, zone=zone, instance=instance).execute()
    status = result['status']
    logger.info(f"{instance} status: {status} should_run: {should_run}")

    action = None
    if should_run and status != 'RUNNING':
        action = 'start'
    elif not should_run and status == 'RUNNING':
        action = 'stop'

    if action:
        payload = {
            "vm_name": instance,
            "action": action,
            "zone": zone,
            "project_id": project
        }
        logger.info(f"payload: {payload}")
        response = requests.post(vmops_api, json=payload)
        if response.status_code == 200:
            logger.info(f"Action '{action}' for VM {instance} pushed successfully.")
        else:
            logger.error(f"Failed to push action '{action}' for VM {instance}.", error=response.text)

def process_instance(project, zone):
    compute = build('compute', 'v1', credentials=credentials)
    result = compute.instances().list(project=project, zone=zone).execute()
    instances = result.get('items', [])

    for instance in instances:
        labels = instance.get('labels', {})
        logger.info(f"checking instance: {instance['name']}")
        if 'managedschedule' not in labels:
            logger.info(f"skipping instance: {instance['name']}")
            continue
        logger.info(f"Processing instance: {instance['name']}")
        label_value = labels['managedschedule']
        try:
            days, start, end, tz = parse_schedule_label(label_value)
            should_run = is_within_schedule(days, start, end, tz)
            manage_vm(compute, instance['name'], project, zone, should_run)
        except ValueError as e:
            logger.error(f"Skipping instance {instance['name']} due to label parsing error", error=str(e))
            continue

def main():
    project = "extended-web-339507"
    zone = "us-central1-a"
    process_instance(project, zone)

if __name__ == "__main__":
    main()