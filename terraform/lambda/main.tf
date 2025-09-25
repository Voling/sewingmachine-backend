data "archive_file" "api_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../src/api"
  output_path = "${path.root}/../build/api.zip"
}

data "archive_file" "jobs_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../src/jobs"
  output_path = "${path.root}/../build/jobs.zip"
}

resource "aws_lambda_function" "health" {
  function_name    = "${var.project_name}-health"
  role             = var.lambda_role_arn
  handler          = "health.lambda_handler"
  runtime          = "python3.11"
  filename         = data.archive_file.api_zip.output_path
  source_code_hash = data.archive_file.api_zip.output_base64sha256
  timeout          = 3
  memory_size      = 128
  architectures    = ["x86_64"]

  environment {
    variables = {
      ALLOWED_ORIGIN = var.allowed_origin
    }
  }

  tags = var.tags
}

resource "aws_lambda_function" "run" {
  function_name    = "${var.project_name}-run"
  role             = var.lambda_role_arn
  handler          = "run.lambda_handler"
  runtime          = "python3.11"
  filename         = data.archive_file.api_zip.output_path
  source_code_hash = data.archive_file.api_zip.output_base64sha256
  timeout          = 3
  memory_size      = 128
  architectures    = ["x86_64"]

  environment {
    variables = {
      DDB_TABLE           = var.ddb_table_name
      ORCHESTRATOR_FN     = aws_lambda_function.orchestrator.function_name
      BRONZE_PREFIX_S3    = var.bronze_prefix_s3
      SILVER_PREFIX_S3    = var.silver_prefix_s3
      GOLD_PREFIX_S3      = var.gold_prefix_s3
      PRESIGN_TTL_SECONDS = "900"
      MAX_DIRS_PER_LAYER  = "25"
      MAX_FILES_PER_DIR   = "50"
      ALLOWED_ORIGIN      = var.allowed_origin
    }
  }

  tags = var.tags
}

resource "aws_lambda_function" "orchestrator" {
  function_name    = "${var.project_name}-orchestrator"
  role             = var.lambda_role_arn
  handler          = "orchestrator.lambda_handler"
  runtime          = "python3.11"
  filename         = data.archive_file.jobs_zip.output_path
  source_code_hash = data.archive_file.jobs_zip.output_base64sha256
  timeout          = 3
  memory_size      = 128
  architectures    = ["x86_64"]

  environment {
    variables = {
      DMS_TASK_ARN               = var.dms_task_arn
      FIXED_RUN                  = var.fixed_run
      EVENTBUS_NAME              = var.event_bus_name
      ATHENA_RUNNER_FUNCTION_ARN = aws_lambda_function.athena_runner.arn
    }
  }

  tags = var.tags
}

resource "aws_lambda_function" "athena_runner" {
  function_name    = "${var.project_name}-athena-runner"
  role             = var.lambda_role_arn
  handler          = "athena_runner.handler"
  runtime          = "python3.11"
  filename         = data.archive_file.jobs_zip.output_path
  source_code_hash = data.archive_file.jobs_zip.output_base64sha256
  timeout          = 3
  memory_size      = 128
  architectures    = ["x86_64"]

  environment {
    variables = {
      ATHENA_OUTPUT  = var.athena_output
      ATHENA_WG      = var.athena_wg
      ATHENA_CATALOG = var.athena_catalog
      EVENTBUS_NAME  = var.event_bus_name
    }
  }

  tags = var.tags
}

resource "aws_lambda_function" "query" {
  function_name    = "${var.project_name}-query"
  role             = var.lambda_role_arn
  handler          = "query.lambda_handler"
  runtime          = "python3.11"
  filename         = data.archive_file.api_zip.output_path
  source_code_hash = data.archive_file.api_zip.output_base64sha256
  timeout          = 3
  memory_size      = 128
  architectures    = ["x86_64"]

  environment {
    variables = {
      ATHENA_OUTPUT  = var.athena_output
      ATHENA_WG      = var.athena_wg
      ATHENA_CATALOG = var.athena_catalog
      ALLOWED_ORIGIN = var.allowed_origin
    }
  }

  tags = var.tags
}

resource "aws_lambda_function" "schemas" {
  function_name    = "${var.project_name}-schemas"
  role             = var.lambda_role_arn
  handler          = "schemas.lambda_handler"
  runtime          = "python3.11"
  filename         = data.archive_file.api_zip.output_path
  source_code_hash = data.archive_file.api_zip.output_base64sha256
  timeout          = 3
  memory_size      = 128
  architectures    = ["x86_64"]

  environment {
    variables = {
      ALLOWED_ORIGIN = var.allowed_origin
    }
  }

  tags = var.tags
}

resource "aws_lambda_function" "materialize" {
  function_name    = "${var.project_name}-materialize"
  role             = var.lambda_role_arn
  handler          = "materialize.lambda_handler"
  runtime          = "python3.11"
  filename         = data.archive_file.api_zip.output_path
  source_code_hash = data.archive_file.api_zip.output_base64sha256
  timeout          = 3
  memory_size      = 128
  architectures    = ["x86_64"]

  environment {
    variables = {
      ALLOWED_ORIGIN = var.allowed_origin
      ATHENA_OUTPUT  = var.athena_output
      ATHENA_WG      = var.athena_wg
    }
  }

  tags = var.tags
}

output "invoke_arns" {
  value = {
    health      = aws_lambda_function.health.invoke_arn
    run         = aws_lambda_function.run.invoke_arn
    query       = aws_lambda_function.query.invoke_arn
    schemas     = aws_lambda_function.schemas.invoke_arn
    materialize = aws_lambda_function.materialize.invoke_arn
  }
}

output "names" {
  value = {
    health        = aws_lambda_function.health.function_name
    run           = aws_lambda_function.run.function_name
    query         = aws_lambda_function.query.function_name
    schemas       = aws_lambda_function.schemas.function_name
    materialize   = aws_lambda_function.materialize.function_name
    orchestrator  = aws_lambda_function.orchestrator.function_name
    athena_runner = aws_lambda_function.athena_runner.function_name
  }
}
