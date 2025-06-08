from google.cloud import container_v1
from google.auth import default
from dataclasses import dataclass, asdict
import json
from typing import List, Optional
import redis
import structlog
import os
import sys
#import app.log_config as _

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.config_loader import load_config
load_config()
r = redis.Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), db=0, decode_responses=True)
logger = structlog.get_logger()
credentials, project_id = default()
client = container_v1.ClusterManagerClient(credentials=credentials)
custom_timeout = 120

@dataclass
class GKEClusterInfo:
    name: str
    location: str
    status: str
    node_count: int
    master_version: str
    endpoint: str
    project_id: str
    autopilot: Optional[bool] = None
    node_version: Optional[str] = None

  
def store_nodepools(cluster_name: str, location: str, project_id: str):
    try:
        parent = f"projects/{project_id}/locations/{location}/clusters/{cluster_name}"
        response = client.list_node_pools(parent=parent, timeout=custom_timeout)
        for nodepool in response.node_pools:
            key = f"gcp_nodepool:{cluster_name}:{nodepool.name}"
            data = {
                "min_node_count": nodepool.autoscaling.min_node_count if nodepool.autoscaling else 0,
                "max_node_count": nodepool.autoscaling.max_node_count if nodepool.autoscaling else 0,
                "desired_node_count": nodepool.initial_node_count,  # You may also use current_node_count if needed
                "autoscaling": nodepool.autoscaling.enabled if nodepool.autoscaling else False
            }

            nodepool_key = f"nodepool:{cluster_name}:{nodepool.name}"
            r.set(nodepool_key, json.dumps(data))
            r.sadd(f"gke:nodepools:{cluster_name}", nodepool.name)
            logger.info("Stored nodepool", nodepool_key=key, data=data)
    except Exception as e:
        logger.error("Failed to store nodepools", cluster=cluster_name, error=str(e))


def fetch_gke_clusters() -> List[GKEClusterInfo]:
    logger.info("Using project_id", project_id=project_id)
    parent = f"projects/{project_id}/locations/-"  # All regions
    response = client.list_clusters(parent=parent, timeout = custom_timeout)
    clusters = response.clusters

    if not clusters:
        print("No clusters found.")
        logger.info("No clusters found.")
        # Optionally, you can raise an exception or return an empty list
        return []
    cluster_list: List[GKEClusterInfo] = []

    for cluster in clusters:
            info = GKEClusterInfo(
                name=cluster.name,
                location=cluster.location,
                status=cluster.status.name,
                node_count=cluster.current_node_count,
                master_version=cluster.current_master_version,
                endpoint=cluster.endpoint,
                project_id=project_id,
                autopilot=cluster.autopilot.enabled if cluster.autopilot else False
            )
            cluster_list.append(info)
    return cluster_list


def main():
    clusters = fetch_gke_clusters()
    inventory_key = "gke:clusters"
    if not clusters:
        logger.info("No GKE clusters found.")
    else:
        for cluster in clusters:
            logger.info("Cluster info", cluster=cluster)
            cluster_key = f"gke:cluster:{cluster.name}"
            try:
                r.set(cluster_key, json.dumps(asdict(cluster)))
                r.sadd(inventory_key, cluster.name)
                logger.info("Cluster added to Redis", cluster_key=cluster_key)
                # Fetch nodepools only for non-Autopilot clusters
                if not cluster.autopilot:
                    logger.info("Cluster is not Autopilot; storing nodepools", cluster=cluster.name)
                    store_nodepools(cluster.name, cluster.location, cluster.project_id)
                else:
                    logger.info("Cluster is Autopilot; skipping nodepool fetch", cluster=cluster.name)
            except redis.RedisError as e:
                logger.error("Redis error", error=str(e))
            # Connect to Redis


if __name__ == "__main__":
    main()
