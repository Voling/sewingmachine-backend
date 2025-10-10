# AWS Sewing Machine

## Overview
The backend runs on AWS Lambda behind API Gateway REST endpoints. Each handler forwards requests to layered Python services (config, domain, infrastructure, application, presentation). Terraform provisions the entire stack: Lambdas, API Gateway resources, Cognito authorizer, DynamoDB cooldown table, Athena orchestration Lambdas, DMS permissions, SSM parameters, and custom domains.

## Core Responsibilities
- **Run** (`POST /run`): acquires a DynamoDB cooldown lock, invokes the orchestration Lambda, and responds with bronze/silver/gold S3 snapshots (presigned URLs included).
- **Orchestrator** Lambda: starts the configured AWS DMS task, creates an EventBridge rule, and grants Events permission to invoke the Athena runner.
- **Athena Runner** Lambda: runs CTAS/MERGE/UPDATE statements that advance the Lakehouse layers and removes the temporary EventBridge rule when finished.
- **Materialize** (`POST /materialize`): validates user SQL, emits INSERT/CTAS statements, submits them to Athena, and waits for completion.
- **Query** (`POST /query`): starts or resumes Athena queries, paginates results, and returns column metadata + execution statistics.
- **Schemas** (`GET /schemas`): lists Glue Data Catalog databases and tables.
- **Health** (`GET /health`): healthcheck.

## Architecture
- **Authentication:** The Cognito authorizer protects every business route. CORS preflight `OPTIONS` requests remain open because browsers cannot attach Cognito tokens to preflights.
- **Configuration:** Terraform writes environment data to SSM Parameter Store. `app/config/settings.py` exposes cached helpers that read environment variables injected into each Lambda.
- **AWS Clients:** `app/infrastructure/aws_clients.py` memoizes `boto3` clients to abstract away low-level clients.

## Terraform Layout
- `terraform/main.tf` - root module wiring and shared tags.
- `terraform/apigw` - REST resources, Cognito authorizer, custom domain settings.
- `terraform/lambda` - Lambda layer packaging and environment variables.
- `terraform/dynamodb` - full load cooldown table definition.
- `terraform/iam` - execution-role policies for S3, DynamoDB, Lambda's invoke permission, DMS, EventBridge, and Athena.
- `terraform/ssm` - Parameter Store entries consumed at runtime.
- `terraform/sewingmachine.tfvars` - environment variables.

The DMS -> EventBridge -> Athena runner flow is captured in Terraform so IAM boundaries and orchestration state stay reproducible across environments.

## Code Structure
```
src/
  api/
    handlers/        # Lambda entrypoints
    app/
      config/        # Settings loaders
      domain/        # Entities and domain errors
      infrastructure/ # Cloud infra adapters
      application/   # Use-case services
      presentation/  # HTTP helpers and logging
  jobs/
    athena_runner.py
    orchestrator.py
```
Tests live in `tests/` and cover configuration, domain models, services, handlers, and jobs. Run them with:
```bash
python -m pytest tests
```

## Quality & Delivery
- **Static analysis:**
  ```bash
  pysonar --sonar-host-url=http://localhost:9000 \
          --sonar-project-key=awssewingmachine \
          --sonar-token=<token>
  ```

## Local Development
1. Export environment variables (or maintain a `.env`) that match SSM parameters. No `python-dotenv` layer is required.
2. Install dependencies: `pip install -r src/api/requirements.txt`
3. Run `python -m pytest tests` before deploying changes.
