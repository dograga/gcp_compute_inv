import redis
import json
import structlog
from dataclasses import dataclass, asdict
from typing import List

@dataclass
class ProjectInfo:
    project_id: str
    name: str
    regions: List[str]

logger = structlog.get_logger()
r = redis.Redis(host='localhost', port=6379, db=0)
#r = redis.Redis(host='10.38.229.3', port=6379, db=0)
# List of projects

projects = [{"project_id":"extended-web-339507", "name":"First Project", "regions":["us-central1"]}]

def get_projects() -> List[ProjectInfo]:
    project_list: List[ProjectInfo] = []
    for project in projects:
            info = ProjectInfo(
                name=project['name'],
                project_id=project['project_id'],
                regions=project['regions']
            )
            project_list.append(info)
    return project_list
    
def main():
    # Store list of keys in gcp:projects
    projects= get_projects()
    for proj in projects:
        print(proj)
        print(type(proj))
        key = f"gcp:project:{proj.project_id}"
        r.set(key, json.dumps(asdict(proj)))              # Store individual project details
        r.sadd("gcp:projects", proj.project_id)            # Add key to master list
    logger.info("Projects added to Redis", projects=projects)

if __name__ == "__main__":
    main()
