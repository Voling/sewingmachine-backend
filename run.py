import os, json, time, uuid, datetime
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "us-west-1")
ORCHESTRATOR_FN = os.environ["ORCHESTRATOR_FN"]
DDB_TABLE = os.environ["DDB_TABLE"]
RESOURCE_KEY = os.environ.get("RESOURCE_KEY", "full-load")
COOLDOWN_SECONDS = int(os.environ.get("COOLDOWN_SECONDS", "30"))  # seconds
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")

# S3 layer roots (can include {run} placeholder)
BRONZE_PREFIX_S3 = os.environ.get("BRONZE_PREFIX_S3")  # e.g., s3://fabric-aws-poc/bronze/
SILVER_PREFIX_S3 = os.environ.get("SILVER_PREFIX_S3")  # e.g., s3://fabric-aws-poc/silver/
GOLD_PREFIX_S3   = os.environ.get("GOLD_PREFIX_S3")    # e.g., s3://fabric-aws-poc/gold/

# Presign + listing limits
PRESIGN_TTL_SECONDS = int(os.environ.get("PRESIGN_TTL_SECONDS", "900"))  # 15 minutes
MAX_DIRS_PER_LAYER  = int(os.environ.get("MAX_DIRS_PER_LAYER", "25"))
MAX_FILES_PER_DIR   = int(os.environ.get("MAX_FILES_PER_DIR", "50"))

# -------------------- CLIENTS --------------------
load_dotenv()
ddb     = boto3.client("dynamodb", region_name=REGION)
lambda_ = boto3.client("lambda",    region_name=REGION)
s3      = boto3.client("s3",        region_name=REGION)

# -------------------- HTTP RESP --------------------
def _resp(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "OPTIONS,POST"
        },
        "body": json.dumps(body)
    }

# -------------------- S3 HELPERS --------------------
def _parse_s3_uri(uri):
    """
    Returns (bucket, key_prefix) and ensures the key prefix ends with '/' if present.
    """
    if not uri or not uri.startswith("s3://"):
        raise ValueError(f"Bad S3 URI: {uri}")
    rest = uri[5:]
    bucket, _, key = rest.partition("/")
    if key and not key.endswith("/"):
        key += "/"
    return bucket, key  # key may be empty ""

def _format_prefix(template, run_str):
    """
    Supports {run} placeholder in the prefix template.
    """
    return (template or "").format(run=run_str)

def _list_immediate_subdirs(bucket, base_prefix, limit):
    """
    List immediate child 'directories' under base_prefix (no recursion).
    Returns (subdir_prefixes, truncated_bool).
    """
    subdirs, truncated = [], False
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=base_prefix, Delimiter="/"):
        for cp in page.get("CommonPrefixes", []) or []:
            subdirs.append(cp["Prefix"])
            if len(subdirs) >= limit:
                truncated = True
                return subdirs, truncated
    return subdirs, truncated

def _list_parquet_recursive(bucket, dir_prefix, limit):
    """
    Recursively list .parquet keys under dir_prefix (handles partitioned layouts).
    Returns (files, truncated_bool) where files are dicts with key/size/lastModified.
    """
    files, truncated = [], False
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=dir_prefix):
        for obj in page.get("Contents", []) or []:
            key = obj["Key"]
            if key.lower().endswith(".parquet"):
                files.append({
                    "key": key,
                    "size": obj.get("Size"),
                    "lastModified": (
                        obj.get("LastModified").strftime("%Y-%m-%dT%H:%M:%SZ")
                        if obj.get("LastModified") else None
                    )
                })
                if len(files) >= limit:
                    truncated = True
                    return files, truncated
    return files, truncated

def _presign(bucket, key, ttl):
    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=ttl
    )

def _layer_tree(prefix_uri, run_str):
    """
    Build a hierarchical listing for a layer:
    {
      "prefix": "s3://bucket/path/",
      "dirCount": N,
      "dirs": [
        {
          "name": "childA/",            # relative to base
          "prefix": "s3://bucket/path/childA/",
          "fileCount": M,
          "files": [
            {"key":"...parquet","size":123,"lastModified":"...","url":"https://..."},
            ...
          ],
          "truncated": false
        },
        ...
      ],
      "truncated": false
    }
    """
    if not prefix_uri:
        return {"prefix": None, "dirCount": 0, "dirs": [], "truncated": False}

    expanded = _format_prefix(prefix_uri, run_str)
    bucket, base_prefix = _parse_s3_uri(expanded)

    # 1) find immediate subdirs
    subdirs, dirs_trunc = _list_immediate_subdirs(bucket, base_prefix, MAX_DIRS_PER_LAYER)

    # If there are no immediate subdirs, treat base as one dir and list files there (recursive)
    if not subdirs:
        files, f_trunc = _list_parquet_recursive(bucket, base_prefix, MAX_FILES_PER_DIR)
        for f in files:
            f["url"] = _presign(bucket, f["key"], PRESIGN_TTL_SECONDS)
        # derive a simple name for the base
        base_name = base_prefix.rstrip("/") if base_prefix else ""
        base_name = (base_name.split("/")[-1] + "/") if base_name else "/"
        return {
            "prefix": expanded,
            "dirCount": 1 if files else 0,
            "dirs": [{
                "name": base_name,
                "prefix": f"s3://{bucket}/{base_prefix}",
                "fileCount": len(files),
                "files": files,
                "truncated": f_trunc
            }],
            "truncated": False
        }

    # 2) for each subdir, collect parquet files (recursive), sign
    dir_entries = []
    for sprefix in subdirs:
        files, f_trunc = _list_parquet_recursive(bucket, sprefix, MAX_FILES_PER_DIR)
        for f in files:
            f["url"] = _presign(bucket, f["key"], PRESIGN_TTL_SECONDS)
        rel_name = sprefix[len(base_prefix):]  # include trailing '/'
        dir_entries.append({
            "name": rel_name,
            "prefix": f"s3://{bucket}/{sprefix}",
            "fileCount": len(files),
            "files": files,
            "truncated": f_trunc
        })

    return {
        "prefix": expanded,
        "dirCount": len(dir_entries),
        "dirs": dir_entries,
        "truncated": dirs_trunc
    }

# -------------------- HANDLER --------------------
def lambda_handler(event, _ctx):
    # CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return _resp(200, {})

    # parse body: { run?: 'YYYY-MM-DD' }
    try:
        body = json.loads(event.get("body") or "{}")
    except Exception:
        body = {}
    run = body.get("run") or datetime.date.today().isoformat()

    now = int(time.time())
    allow_after = now + COOLDOWN_SECONDS

    # try to place a lock if none exists or expired
    try:
        ddb.put_item(
            TableName=DDB_TABLE,
            Item={
                "resource": {"S": RESOURCE_KEY},
                "allowAfter": {"N": str(allow_after)},
                "lastRun": {"N": str(now)},
                "runId": {"S": str(uuid.uuid4())},
                "expiresAt": {"N": str(allow_after + 3600)}  # TTL safety
            },
            ConditionExpression="attribute_not_exists(#res) OR allowAfter <= :now",
            ExpressionAttributeNames={"#res": "resource"},  # 'resource' is reserved in expressions
            ExpressionAttributeValues={":now": {"N": str(now)}}
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            # fetch current to compute retry
            cur = ddb.get_item(TableName=DDB_TABLE, Key={"resource": {"S": RESOURCE_KEY}}).get("Item", {})
            allowAfter = int(cur.get("allowAfter", {}).get("N", str(now + COOLDOWN_SECONDS)))
            retry = max(0, allowAfter - now)
            # Return 429 with current downloadable view (no orchestration)
            layers = {
                "bronze": _layer_tree(BRONZE_PREFIX_S3, run),
                "silver": _layer_tree(SILVER_PREFIX_S3, run),
                "gold":   _layer_tree(GOLD_PREFIX_S3,   run),
                "ttlSeconds": PRESIGN_TTL_SECONDS
            }
            return _resp(429, {
                "error": {"code": "CooldownActive", "message": "Full load recently triggered."},
                "retryAfterSeconds": retry,
                "run": run,
                "layers": layers
            })
        # other errors bubble up
        raise

    # fire-and-forget the heavy job
    payload = {"run": run, "triggeredAt": datetime.datetime.utcnow().isoformat() + "Z"}
    lambda_.invoke(
        FunctionName=ORCHESTRATOR_FN,
        InvocationType="Event",  # async
        Payload=json.dumps(payload).encode("utf-8")
    )

    # include hierarchical listing + signed URLs for current objects
    layers = {
        "bronze": _layer_tree(BRONZE_PREFIX_S3, run),
        "silver": _layer_tree(SILVER_PREFIX_S3, run),
        "gold":   _layer_tree(GOLD_PREFIX_S3,   run),
        "ttlSeconds": PRESIGN_TTL_SECONDS
    }

    return _resp(202, {
        "status": "accepted",
        "run": run,
        "cooldownSeconds": COOLDOWN_SECONDS,
        "layers": layers
    })