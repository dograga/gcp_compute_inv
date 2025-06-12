import redis
import os
import json
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.config_loader import load_config
load_config()

r = redis.Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), db=0, decode_responses=True)
# Define your Redis Set key
REDIS_SET = "vm:scheduler"

def main():
    try:
        # Fetch all keys from the Redis set
        keys = r.smembers(REDIS_SET)
        if not keys:
            print(f"No keys found in Redis set: {REDIS_SET}")
            return

        print(f"Found {len(keys)} keys in Redis set: {REDIS_SET}\n")

        # Fetch and print each key-value pair
        for key in keys:
            value = r.get(key)
            if value:
                try:
                    value_json = json.loads(value)
                    print(f"Key: {key}\nValue: {json.dumps(value_json, indent=2)}\n")
                except json.JSONDecodeError:
                    print(f"Key: {key}\nValue: {value} (Non-JSON format)\n")
            else:
                print(f"Key: {key} has expired or is empty.\n")

    except Exception as e:
        print(f"Error fetching data from Redis: {str(e)}")

if __name__ == "__main__":
    main()
