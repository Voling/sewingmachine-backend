from __future__ import annotations

import datetime
import json
import os
import uuid
from dataclasses import dataclass
from typing import Optional

import boto3
from botocore.config import Config

CLIENT_CONFIG = Config(connect_timeout=3, read_timeout=10)


dms = boto3.client('dms', config=CLIENT_CONFIG)
events = boto3.client('events', config=CLIENT_CONFIG)
lambda_ = boto3.client('lambda', config=CLIENT_CONFIG)


@dataclass(frozen=True)
class OrchestratorConfig:
    task_arn: str
    event_bus: str
    runner_function_arn: str
    default_run: str


@dataclass(frozen=True)
class TriggerRunCommand:
    run: Optional[str]


@dataclass(frozen=True)
class TriggerRunResult:
    job_id: str
    run: str
    rule_name: str


class OrchestratorService:
    def __init__(self, dms_client, events_client, lambda_client, config: OrchestratorConfig) -> None:
        self._dms = dms_client
        self._events = events_client
        self._lambda = lambda_client
        self._config = config

    def trigger_full_load(self, command: TriggerRunCommand) -> TriggerRunResult:
        job_id = str(uuid.uuid4())
        run_value = command.run or self._config.default_run

        self._dms.start_replication_task(
            ReplicationTaskArn=self._config.task_arn,
            StartReplicationTaskType='reload-target',
        )

        rule_name = f"sewingmachine-dms-finished-{job_id}"
        pattern = {
            "source": ["aws.dms"],
            "detail-type": ["DMS Replication Task State Change"],
            "detail": {
                "ReplicationTaskArn": [self._config.task_arn],
                "ReplicationTaskState": ["full-load-completed"],
            },
        }
        response = self._events.put_rule(
            Name=rule_name,
            EventPattern=json.dumps(pattern),
            State='ENABLED',
            EventBusName=self._config.event_bus,
        )
        rule_arn = response.get('RuleArn')

        target_input = json.dumps({
            "jobId": job_id,
            "run": run_value,
            "cleanupRule": rule_name,
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        })
        self._events.put_targets(
            Rule=rule_name,
            EventBusName=self._config.event_bus,
            Targets=[
                {
                    "Id": "athena-runner",
                    "Arn": self._config.runner_function_arn,
                    "Input": target_input,
                }
            ],
        )

        self._lambda.add_permission(
            FunctionName=self._config.runner_function_arn,
            StatementId=f"eb-invoke-{job_id}",
            Action="lambda:InvokeFunction",
            Principal="events.amazonaws.com",
            SourceArn=rule_arn,
        )

        return TriggerRunResult(job_id=job_id, run=run_value, rule_name=rule_name)


def _load_config() -> OrchestratorConfig:
    return OrchestratorConfig(
        task_arn=os.environ['DMS_TASK_ARN'],
        event_bus=os.environ.get('EVENTBUS_NAME', 'default'),
        runner_function_arn=os.environ['ATHENA_RUNNER_FUNCTION_ARN'],
        default_run=os.environ.get('FIXED_RUN', '2025-08-13'),
    )


def _parse_command(event: dict | None) -> TriggerRunCommand:
    payload = event or {}
    if isinstance(payload, str):
        payload = json.loads(payload)
    return TriggerRunCommand(run=payload.get('run'))


def lambda_handler(event, ctx):
    service = OrchestratorService(dms, events, lambda_, _load_config())
    command = _parse_command(event)
    result = service.trigger_full_load(command)
    body = {
        "jobId": result.job_id,
        "status": "accepted",
        "run": result.run,
    }
    return {
        "statusCode": 202,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }
