import os
from dotenv import load_dotenv

def load_config():
    env = os.getenv("ENV", "dev")
    env_file = f"./env/{env}/config.env"

    if not os.path.exists(env_file):
        raise FileNotFoundError(f"[ERROR] Missing config file: {env_file}")

    load_dotenv(env_file)
    print(f"[INFO] Loaded environment: {env}")

    # Validate required variables
    required_vars = ["API_ENDPOINT"]
    for var in required_vars:
        if not os.getenv(var):
            raise RuntimeError(f"[ERROR] Missing required config: {var}")
