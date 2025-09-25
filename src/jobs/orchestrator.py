import json, os, uuid, datetime
import boto3
dms = boto3.client('dms')
events = boto3.client('events')
lambda_ = boto3.client('lambda')

TASK_ARN = os.environ['DMS_TASK_ARN']
EVENTBUS = os.environ.get('EVENTBUS_NAME', 'default')
ATHENA_RUNNER_FN = os.environ['ATHENA_RUNNER_FUNCTION_ARN']

RUN = os.environ.get('FIXED_RUN', '2025-08-13')

def lambda_handler(event, ctx):
    job_id = str(uuid.uuid4())

    dms.start_replication_task(
        ReplicationTaskArn=TASK_ARN,
        StartReplicationTaskType='reload-target'
    )

    rule_name = f"sewingmachine-dms-finished-{job_id}"
    pattern = {
        "source": ["aws.dms"],
        "detail-type": ["DMS Replication Task State Change"],
        "detail": {
            "ReplicationTaskArn": [TASK_ARN],
            "ReplicationTaskState": ["full-load-completed"]
        }
    }
    r = events.put_rule(
        Name=rule_name,
        EventPattern=json.dumps(pattern),
        State='ENABLED',
        EventBusName=EVENTBUS
    )
    rule_arn = r.get('RuleArn')

    target_input = json.dumps({
        "jobId": job_id,
        "run": RUN,
        "cleanupRule": rule_name
    })
    events.put_targets(
        Rule=rule_name,
        EventBusName=EVENTBUS,
        Targets=[{
            "Id": "athena-runner",
            "Arn": ATHENA_RUNNER_FN,
            "Input": target_input
        }]
    )

    lambda_.add_permission(
        FunctionName=ATHENA_RUNNER_FN,
        StatementId=f"eb-invoke-{job_id}",
        Action="lambda:InvokeFunction",
        Principal="events.amazonaws.com",
        SourceArn=rule_arn
    )

    return {
        "statusCode": 202,
        "headers": {"content-type": "application/json"},
        "body": json.dumps({"jobId": job_id, "status": "accepted", "run": RUN})
    }


