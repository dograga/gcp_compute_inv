import redis
import json
from google.cloud import compute_v1
from dataclasses import dataclass, asdict
import structlog
from typing import List

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
r = redis.Redis(host='10.38.229.3', port=6379, db=0)
logger = structlog.get_logger()

@dataclass
class VMInfo:
    vm_name: str
    machine_type: str
    status: str
    zone: str
    cpu_platform: str
    project_id: str
    tags: dict = None

def post_to_redis(vms: VMInfo):
    inventory_key="gcp:vms"
    for vm in vms:
        print(vm)
        logger.info("Update VM info to redis", VM=vm)
        vm_key = f"gcp:vm:{vm.vm_name}"
        project_key = f"gcp:vms:{vm.project_id}"
        vm_key = f"{project_key}:{vm.vm_name}"
        try:
            logger.info(vm)
            # Add project ID to the master project set
            r.sadd(inventory_key, vm.project_id)
            # Add vm name to the set under project ID
            r.sadd(project_key, vm.vm_name)
            # Store VM info
            r.set(vm_key, json.dumps(asdict(vm)))
            logger.info("Cluster added to Redis", vm_key=vm_key)
        except redis.RedisError as e:
            logger.error("Redis error", error=str(e))

def list_all_instances(project_id: str) -> List[VMInfo]:
    """
    List all instances in a project.
    """
    instance_client = compute_v1.InstancesClient()
    try:
        request = compute_v1.AggregatedListInstancesRequest()
        request.project = project_id
        # Use the `max_results` parameter to limit the number of results that the API returns per response page.
        request.max_results = 50
        vmlist: List[VMInfo] = []
        agg_list = instance_client.aggregated_list(request=request)
        for zone, response in agg_list:
            tags = None
            if response.instances:
                for instance in response.instances:
                    logger.info("Instance found", instance=instance.name)
                    if instance.labels:
                        tags = instance.labels
                    info = VMInfo(
                            vm_name=instance.name,
                            zone=zone,
                            status=instance.status,
                            cpu_platform=instance.cpu_platform,
                            machine_type=instance.machine_type,
                            tags=dict(tags),
                            project_id=project_id
                        )
                    vmlist.append(info)    
        return vmlist
    except Exception as e:
        logger.error("Error listing instances", error=str(e))
        return None
        
vms=list_all_instances("extended-web-339507")
post_to_redis(vms)
logger.info("VMs found", vms=vms)
