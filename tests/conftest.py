import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src_dir = ROOT / "src"
api_dir = src_dir / "api"
for path in (str(api_dir), str(src_dir)):
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("ATHENA_OUTPUT", "s3://test-output/")
os.environ.setdefault("ATHENA_WG", "primary")
os.environ.setdefault("ATHENA_CATALOG", "AwsDataCatalog")
os.environ.setdefault("EVENTBUS_NAME", "default")
os.environ.setdefault("DMS_TASK_ARN", "dms-task")
os.environ.setdefault("ATHENA_RUNNER_FUNCTION_ARN", "lambda-arn")
os.environ.setdefault("AWS_REGION", "us-west-1")

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    def load_dotenv():
        return False

# Load .env before importing app modules when available
load_dotenv()
