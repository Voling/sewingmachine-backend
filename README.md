# SewingMachine Backend

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
```
API Gateway (REST + Cognito)
        |
        v
Lambda handlers (src/api/handlers)
        |
        +-- DynamoDB cooldown table
        +-- S3 bronze / silver / gold prefixes
        +-- Athena queries & materialize jobs
        +-- Glue schema discovery
        +-- Lambda invoke (orchestrator)
               |
               +-- EventBridge rule -> DMS task -> Athena runner
```
- **Authentication:** The Cognito authorizer protects every business route. CORS preflight `OPTIONS` requests remain open because browsers cannot attach Cognito tokens to preflights.
- **Configuration:** Terraform writes environment data to SSM Parameter Store. `app/config/settings.py` exposes cached helpers that read environment variables injected into each Lambda.
- **AWS Clients:** `app/infrastructure/aws_clients.py` memoizes `boto3` clients per region to keep handlers fast and easy to test.

## Terraform Layout
- `terraform/main.tf` - root module wiring and shared tags.
- `terraform/apigw` - REST resources, Cognito authorizer, integrations, custom domain, and stage settings.
- `terraform/lambda` - Lambda packaging and environment variables.
- `terraform/dynamodb` - cooldown table definition.
- `terraform/iam` - execution-role policies (S3, DynamoDB, Lambda invoke, DMS, EventBridge, Athena).
- `terraform/ssm` - Parameter Store entries consumed at runtime.
- `terraform/sewingmachine.tfvars` - production defaults (regions, ARNs, domains).

The DMS -> EventBridge -> Athena runner flow is captured in Terraform so IAM boundaries and orchestration state stay reproducible across environments.

## Code Structure
```
src/
  api/
    handlers/        # Lambda entrypoints
    app/
      config/        # Settings loaders
      domain/        # Entities and domain errors
      infrastructure/# AWS client adapters
      application/   # Use-case services (run, query, materialize, schemas, health)
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
- **CI:** `.github/workflows/build.yml` runs linting, tests, and infrastructure steps.
- **Terraform operations:** execute from the `terraform/` directory:
  ```bash
  terraform plan -var-file=terraform/sewingmachine.tfvars
  terraform apply -var-file=terraform/sewingmachine.tfvars
  ```

## Local Development
1. Export environment variables (or maintain a `.env`) that match SSM parameters. No `python-dotenv` layer is required.
2. Install dependencies: `pip install -r src/api/requirements.txt` (currently empty) and `pip install -r src/jobs/requirements.txt` if job-specific dependencies are added later.
3. Run `python -m pytest tests` before deploying changes.

## Operational Notes
- **Cooldown enforcement:** DynamoDB conditional writes prevent duplicate run triggers; responses include `retryAfterSeconds` metadata when throttled.
- **CORS:** Response helpers return the caller origin when it matches the approved list (`https://awssewingmachine.com`, `http://localhost:5173`).
- **Observability:** API Gateway stage logging is enabled at INFO with metrics and request tracing. Handlers use structured logging via `app/presentation/logging.py`.
- **Security:** Lambda permissions are limited to the API Gateway execution ARN. Keep `/health` authenticated unless you provide a separate public status page.