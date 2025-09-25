import os, json, time
import boto3

REGION = os.environ.get("AWS_REGION","us-west-1")
ATHENA_WG = os.environ.get("ATHENA_WG","fabric-wg")
ATHENA_OUTPUT = os.environ["ATHENA_OUTPUT"]
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN","*")
athena = boto3.client("athena", region_name=REGION)

def resp(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "OPTIONS,POST"
        },
        "body": json.dumps(body)
    }

def start_and_wait(sql, db):
    qid = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": db},
        ResultConfiguration={"OutputLocation": ATHENA_OUTPUT},
        WorkGroup=ATHENA_WG
    )["QueryExecutionId"]
    while True:
        st = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]["State"]
        if st in ("SUCCEEDED","FAILED","CANCELLED"):
            if st != "SUCCEEDED":
                reason = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"].get("StateChangeReason","")
                raise RuntimeError(f"Athena {st}: {reason}")
            return qid
        time.sleep(0.5)

def only_select(sql: str) -> bool:
    s = sql.strip().lower()
    if not s.startswith("select"): return False
    banned = [";create ", ";drop ", ";alter ", " insert ", " merge ", " delete ", " update "]
    return not any(b in s for b in banned)

def lambda_handler(event, _ctx):
    if event.get("httpMethod") == "OPTIONS":
        return resp(200, {})

    try:
        body = json.loads(event.get("body") or "{}")
    except Exception:
        return resp(400, {"error":{"code":"BadJson","message":"Invalid JSON"}})

    target = body.get("target") or {}
    db = target.get("db")
    tbl = target.get("table")
    mode = (body.get("mode") or "append").lower()
    select_sql = body.get("sql")
    props = body.get("properties") or {}

    if not db or not tbl or not select_sql:
        return resp(400, {"error":{"code":"MissingParam","message":"target.db, target.table and sql are required"}})
    if mode not in ("append","replace"):
        return resp(400, {"error":{"code":"BadParam","message":"mode must be append or replace"}})
    if not only_select(select_sql):
        return resp(400, {"error":{"code":"UnsafeSql","message":"sql must be a SELECT statement"}})

    if mode == "replace":
        props_sql = ", ".join(f"'{k}' = '{v}'" for k,v in props.items()) if props else "table_type = 'ICEBERG', format = 'PARQUET'"
        sql = f"DROP TABLE IF EXISTS {db}.{tbl};\nCREATE TABLE {db}.{tbl} WITH ({props_sql}) AS {select_sql}"
    else:
        sql = f"INSERT INTO {db}.{tbl} {select_sql}"

    qid = start_and_wait(sql, db)
    return resp(200, {"status":"ok","table":f"{db}.{tbl}","mode":mode,"qid":qid})


