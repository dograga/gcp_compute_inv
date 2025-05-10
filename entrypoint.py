import sys
import subprocess

def run(module_name):
    path_map = {
        "gke": "gke/main.py",
        "vms": "vms/main.py",
        "projects": "projects/main.py",
    }
    if module_name not in path_map:
        print(f"Unknown module: {module_name}")
        sys.exit(1)

    subprocess.run(["python", path_map[module_name]], check=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: entrypoint.py [gke|vms|projects]")
        sys.exit(1)

    run(sys.argv[1].lower())
