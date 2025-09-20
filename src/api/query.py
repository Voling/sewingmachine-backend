import os, json, time
from dotenv import load_dotenv
import boto3

REGION = os.environ.get("AWS_REGION", "us-west-1")
ATHENA_WG = os.environ.get("ATHENA_WG", "primary")
ATHENA_OUTPUT = os.environ["ATHENA_OUTPUT"]
ATHENA_CATALOG = os.environ.get("ATHENA_CATALOG", "AwsDataCatalog")
ATHENA_DEFAULT_DB = os.environ.get("ATHENA_DEFAULT_DB")
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")

load_dotenv()
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

def start_and_wait(sql, database):
    qctx = {"Catalog": ATHENA_CATALOG}
    if database:
        qctx["Database"] = database
    elif ATHENA_DEFAULT_DB:
        qctx["Database"] = ATHENA_DEFAULT_DB

    q = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext=qctx,
        ResultConfiguration={"OutputLocation": ATHENA_OUTPUT},
        WorkGroup=ATHENA_WG
    )
    qid = q["QueryExecutionId"]
    while True:
        qe = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]
        st = qe["Status"]["State"]
        if st in ("SUCCEEDED","FAILED","CANCELLED"):
            return qid, qe
        time.sleep(0.4)

def read_page(qid, token=None, max_rows=500):
    kw = {"QueryExecutionId": qid, "MaxResults": max_rows}
    if token: kw["NextToken"] = token
    out = athena.get_query_results(**kw)
    cols = [c.get("Label") or c.get("Name") for c in out["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]]
    rows = []
    start_index = 1 if not token and out["ResultSet"]["Rows"] else 0
    for r in out["ResultSet"]["Rows"][start_index:]:
        rows.append([d.get("VarCharValue") if "VarCharValue" in d else None for d in r["Data"]])
    return cols, rows, out.get("NextToken")

def lambda_handler(event, _ctx):
    if event.get("httpMethod") == "OPTIONS":
        return resp(200, {})

    try:
        body = json.loads(event.get("body") or "{}")
    except Exception:
        return resp(400, {"error":{"code":"BadJson","message":"Invalid JSON body"}})

    sql   = body.get("sql")
    db    = (body.get("catalog") or body.get("database") or "").strip() or None
    token = body.get("nextPageToken")
    qid   = body.get("queryExecutionId")
    maxr  = min(max(1, int(body.get("maxRows") or 500)), 1000)

    if not (sql or qid):
        return resp(400, {"error":{"code":"MissingParam","message":"sql or queryExecutionId required"}})

    stats = {}
    if not token and not qid:
        qid, qe = start_and_wait(sql, db)
        s = qe.get("Statistics", {})
        stats = {
            "scannedBytes": s.get("DataScannedInBytes"),
            "executionTimeMs": s.get("EngineExecutionTimeInMillis")
        }

    cols, rows, next_token = read_page(qid or body["queryExecutionId"], token, max_rows=maxr)
    return resp(200, {
        "columns": cols,
        "rows": rows,
        "stats": stats,
        "queryExecutionId": qid or body["queryExecutionId"],
        "nextPageToken": next_token
    })


