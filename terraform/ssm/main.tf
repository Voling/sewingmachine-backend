resource "aws_ssm_parameter" "allowed_origin" {
  name  = "/sewingmachine/ALLOWED_ORIGIN"
  type  = "String"
  value = var.allowed_origin
}

resource "aws_ssm_parameter" "athena_output"  {
  name  = "/sewingmachine/ATHENA_OUTPUT"
  type  = "String"
  value = var.athena_output
}

resource "aws_ssm_parameter" "athena_wg"      {
  name  = "/sewingmachine/ATHENA_WG"
  type  = "String"
  value = var.athena_wg
}

resource "aws_ssm_parameter" "athena_catalog" {
  name  = "/sewingmachine/ATHENA_CATALOG"
  type  = "String"
  value = var.athena_catalog
}

resource "aws_ssm_parameter" "bronze_prefix"  {
  name  = "/sewingmachine/BRONZE_PREFIX_S3"
  type  = "String"
  value = var.bronze_prefix_s3
}

resource "aws_ssm_parameter" "silver_prefix"  {
  name  = "/sewingmachine/SILVER_PREFIX_S3"
  type  = "String"
  value = var.silver_prefix_s3
}

resource "aws_ssm_parameter" "gold_prefix"    {
  name  = "/sewingmachine/GOLD_PREFIX_S3"
  type  = "String"
  value = var.gold_prefix_s3
}

resource "aws_ssm_parameter" "ddb_table"      {
  name  = "/sewingmachine/DDB_TABLE"
  type  = "String"
  value = var.ddb_table_name
}

resource "aws_ssm_parameter" "fixed_run"      {
  name  = "/sewingmachine/FIXED_RUN"
  type  = "String"
  value = var.fixed_run
}

resource "aws_ssm_parameter" "event_bus"      {
  name  = "/sewingmachine/EVENTBUS_NAME"
  type  = "String"
  value = var.event_bus_name
}

resource "aws_ssm_parameter" "cognito_pool"   {
  name  = "/sewingmachine/COGNITO_USER_POOL_ID"
  type  = "String"
  value = var.cognito_user_pool_id
}

resource "aws_ssm_parameter" "dms_task_arn"   {
  name  = "/sewingmachine/DMS_TASK_ARN"
  type  = "String"
  value = var.dms_task_arn
}

