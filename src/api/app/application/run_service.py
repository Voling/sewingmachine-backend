from __future__ import annotations

import datetime
import json
import time
import uuid
from typing import Dict, Optional
from botocore.exceptions import ClientError

from ..config.settings import RunSettings
from ..domain.errors import CooldownActiveError, ValidationError
from ..domain.models import DirectoryDescriptor, FileDescriptor, LayerSnapshot
from ..infrastructure.aws_clients import AwsClients
from ..presentation.logging import get_logger


_LOGGER = get_logger("sewingmachine.run")


class RunService:
    def __init__(self, settings: RunSettings, clients: AwsClients) -> None:
        self._settings = settings
        self._ddb = clients.dynamodb()
        self._lambda = clients.lambda_()
        self._s3 = clients.s3()

    def execute(self, payload: Optional[Dict]) -> Dict:
        run_value = (payload or {}).get("run") or datetime.date.today().isoformat()
        now = int(time.time())
        allow_after = now + self._settings.cooldown_seconds

        self._acquire_cooldown(now, allow_after, run_value)
        self._invoke_orchestrator(run_value)
        layers = self._build_layers(run_value)

        return {
            "status": "accepted",
            "run": run_value,
            "cooldownSeconds": self._settings.cooldown_seconds,
            "layers": layers,
        }

    def _acquire_cooldown(self, now: int, allow_after: int, run_value: str) -> None:
        try:
            self._ddb.put_item(
                TableName=self._settings.cooldown_table_name,
                Item={
                    "resource": {"S": self._settings.resource_key},
                    "allowAfter": {"N": str(allow_after)},
                    "lastRun": {"N": str(now)},
                    "runId": {"S": str(uuid.uuid4())},
                    "expiresAt": {"N": str(allow_after + 3600)},
                },
                ConditionExpression="attribute_not_exists(#res) OR allowAfter <= :now",
                ExpressionAttributeNames={"#res": "resource"},
                ExpressionAttributeValues={":now": {"N": str(now)}},
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise
            current = self._ddb.get_item(
                TableName=self._settings.cooldown_table_name,
                Key={"resource": {"S": self._settings.resource_key}},
            ).get("Item", {})
            allow_after_existing = int(current.get("allowAfter", {}).get("N", str(allow_after)))
            retry_after = max(0, allow_after_existing - now)
            layers = self._build_layers(run_value)
            _LOGGER.info(
                "Cooldown active",
                extra={"retryAfterSeconds": retry_after, "resource": self._settings.resource_key},
            )
            raise CooldownActiveError(retry_after_seconds=retry_after, run=run_value, layers=layers) from exc

    def _invoke_orchestrator(self, run_value: str) -> None:
        payload = {"run": run_value, "triggeredAt": datetime.datetime.utcnow().isoformat() + "Z"}
        self._lambda.invoke(
            FunctionName=self._settings.orchestrator_function,
            InvocationType="Event",
            Payload=json.dumps(payload).encode("utf-8"),
        )

    def _build_layers(self, run_value: str) -> Dict[str, Dict]:
        return {
            "bronze": self._layer_snapshot(self._settings.bronze_prefix, run_value).to_dict(),
            "silver": self._layer_snapshot(self._settings.silver_prefix, run_value).to_dict(),
            "gold": self._layer_snapshot(self._settings.gold_prefix, run_value).to_dict(),
            "ttlSeconds": self._settings.presign_ttl_seconds,
        }

    def _layer_snapshot(self, template: Optional[str], run_value: str) -> LayerSnapshot:
        if not template:
            return LayerSnapshot(prefix=None, dir_count=0, dirs=[], truncated=False)

        expanded_uri = template.format(run=run_value)
        bucket, prefix = self._parse_s3_uri(expanded_uri)

        subdirs, truncated_dirs = self._list_immediate_subdirs(bucket, prefix, self._settings.max_dirs_per_layer)

        if not subdirs:
            files, files_truncated = self._list_parquet_recursive(bucket, prefix, self._settings.max_files_per_dir)
            file_descriptors = [self._decorate_file(bucket, f) for f in files]
            base_name = prefix.rstrip("/").split("/")[-1] + "/" if prefix else "/"
            directory = DirectoryDescriptor(
                name=base_name,
                prefix=f"s3://{bucket}/{prefix}",
                file_count=len(file_descriptors),
                files=file_descriptors,
                truncated=files_truncated,
            )
            return LayerSnapshot(prefix=expanded_uri, dir_count=1 if file_descriptors else 0, dirs=[directory], truncated=False)

        directories: list[DirectoryDescriptor] = []
        for dir_prefix in subdirs:
            files, files_truncated = self._list_parquet_recursive(bucket, dir_prefix, self._settings.max_files_per_dir)
            file_descriptors = [self._decorate_file(bucket, f) for f in files]
            relative_name = dir_prefix[len(prefix):]
            directories.append(
                DirectoryDescriptor(
                    name=relative_name,
                    prefix=f"s3://{bucket}/{dir_prefix}",
                    file_count=len(file_descriptors),
                    files=file_descriptors,
                    truncated=files_truncated,
                )
            )

        return LayerSnapshot(
            prefix=expanded_uri,
            dir_count=len(directories),
            dirs=directories,
            truncated=truncated_dirs,
        )

    def _decorate_file(self, bucket: str, file_info: Dict[str, Optional[str]]) -> FileDescriptor:
        key = file_info.get("key") or ""
        url = self._s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=self._settings.presign_ttl_seconds,
        )
        return FileDescriptor(
            key=key,
            size=file_info.get("size"),
            last_modified=file_info.get("lastModified"),
            url=url,
        )

    def _parse_s3_uri(self, uri: str) -> tuple[str, str]:
        if not uri or not uri.startswith("s3://"):
            raise ValidationError("Invalid S3 URI", code="BadS3Uri")
        remainder = uri[5:]
        bucket, _, key = remainder.partition("/")
        if key and not key.endswith("/"):
            key += "/"
        return bucket, key

    def _list_immediate_subdirs(self, bucket: str, base_prefix: str, limit: int):
        prefixes: list[str] = []
        truncated = False
        paginator = self._s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=base_prefix, Delimiter="/"):
            for cp in page.get("CommonPrefixes", []) or []:
                prefixes.append(cp["Prefix"])
                if len(prefixes) >= limit:
                    truncated = True
                    return prefixes, truncated
        return prefixes, truncated

    def _list_parquet_recursive(self, bucket: str, dir_prefix: str, limit: int):
        files: list[Dict[str, Optional[str]]] = []
        truncated = False
        paginator = self._s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=dir_prefix):
            for obj in page.get("Contents", []) or []:
                key = obj["Key"]
                if key.lower().endswith(".parquet"):
                    files.append(
                        {
                            "key": key,
                            "size": obj.get("Size"),
                            "lastModified": (
                                obj.get("LastModified").strftime("%Y-%m-%dT%H:%M:%SZ")
                                if obj.get("LastModified")
                                else None
                            ),
                        }
                    )
                    if len(files) >= limit:
                        truncated = True
                        return files, truncated
        return files, truncated
