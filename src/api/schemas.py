import os, json
from dotenv import load_dotenv
import boto3

REGION = os.environ.get("AWS_REGION","us-west-1")
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN","*")
load_dotenv()
glue = boto3.client("glue", region_name=REGION)

def resp(body):
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "OPTIONS,GET"
        },
        "body": json.dumps(body)
    }

def lambda_handler(event, _ctx):
    if event.get("httpMethod") == "OPTIONS":
        return resp({})
    dbs = []
    paginator = glue.get_paginator("get_databases")
    for page in paginator.paginate():
        for db in page.get("DatabaseList", []):
            name = db["Name"]
            tables = []
            tp = glue.get_paginator("get_tables")
            for tpage in tp.paginate(DatabaseName=name, PaginationConfig={"MaxItems": 200}):
                for t in tpage.get("TableList", []):
                    tables.append(t["Name"])
            dbs.append({"name": name, "tables": tables})
    return resp({"databases": dbs})


