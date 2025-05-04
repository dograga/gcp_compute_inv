from google.cloud import container_v1
from google.auth import default
from dataclasses import dataclass, asdict
import json
from typing import List, Optional
import redis
import structlog
#import app.log_config as _

logger = structlog.get_logger()

@dataclass
class GKEClusterInfo:
    name: str
    location: str
    status: str
    node_count: int
    master_version: str
    endpoint: str
    project_id: str
    node_version: Optional[str] = None

def fetch_gke_clusters() -> List[GKEClusterInfo]:
    credentials, project_id = default()
    logger.info("Using project_id", project_id=project_id)
    logger.info("Using credentials", credentials=credentials)
    client = container_v1.ClusterManagerClient(credentials=credentials)
    parent = f"projects/{project_id}/locations/-"  # All regions
    response = client.list_clusters(parent=parent)
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
                project_id=project_id
            )
            cluster_list.append(info)
    return cluster_list


def main():
    clusters = fetch_gke_clusters()
    #r = redis.Redis(host='172.22.204.229', port=6379, db=0)
    r = redis.Redis(host='10.80.54.3', port=6379, db=0)
    inventory_key = "gke:clusters"
    if not clusters:
        print("No GKE clusters found.")
    else:
        for cluster in clusters:
            print(cluster)
            logger.info("Cluster info", cluster=cluster)
            cluster_key = f"gke:cluster:{cluster.name}"
            r.set(cluster_key, json.dumps(asdict(cluster)))
            r.sadd(inventory_key, cluster.name)
            # Connect to Redis


if __name__ == "__main__":
    main()
