import os, json, datetime
from dotenv import load_dotenv
load_dotenv()
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN","*")

def lambda_handler(event, _ctx):
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,OPTIONS"
        },
        "body": json.dumps({"status":"ok","time": datetime.datetime.utcnow().isoformat()+"Z"})
    }
