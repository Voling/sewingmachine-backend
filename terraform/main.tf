terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.4"
    }
  }
}

provider "aws" { region = var.aws_region }

locals {
  project_name = var.project_name
  tags         = merge(var.default_tags, { Project = local.project_name })
}

module "iam" {
  source        = "./iam"
  project_name  = local.project_name
  tags          = local.tags
  dms_task_arn  = var.dms_task_arn
  ddb_table_arn = module.dynamodb.table_arn
}

module "dynamodb" {
  source         = "./dynamodb"
  ddb_table_name = var.ddb_table_name
  tags           = local.tags
}

module "lambda" {
  source            = "./lambda"
  project_name      = local.project_name
  lambda_role_arn   = module.iam.lambda_role_arn
  allowed_origin    = var.allowed_origin
  ddb_table_name    = module.dynamodb.table_name
  bronze_prefix_s3  = var.bronze_prefix_s3
  silver_prefix_s3  = var.silver_prefix_s3
  gold_prefix_s3    = var.gold_prefix_s3
  dms_task_arn      = var.dms_task_arn
  fixed_run         = var.fixed_run
  event_bus_name    = var.event_bus_name
  athena_output     = var.athena_output
  athena_wg         = var.athena_wg
  athena_catalog    = var.athena_catalog
  tags              = local.tags
}

module "apigw" {
  source                 = "./apigw"
  project_name           = local.project_name
  aws_region             = var.aws_region
  cognito_user_pool_id   = var.cognito_user_pool_id
  tags                   = local.tags
  lambda_health_invoke_arn  = module.lambda.invoke_arns["health"]
  lambda_run_invoke_arn     = module.lambda.invoke_arns["run"]
  lambda_query_invoke_arn   = module.lambda.invoke_arns["query"]
  lambda_schemas_invoke_arn = module.lambda.invoke_arns["schemas"]
  lambda_health_name        = module.lambda.names["health"]
  lambda_run_name           = module.lambda.names["run"]
  lambda_query_name         = module.lambda.names["query"]
  lambda_schemas_name       = module.lambda.names["schemas"]
}

module "ssm" {
  source               = "./ssm"
  allowed_origin       = var.allowed_origin
  athena_output        = var.athena_output
  athena_wg            = var.athena_wg
  athena_catalog       = var.athena_catalog
  bronze_prefix_s3     = var.bronze_prefix_s3
  silver_prefix_s3     = var.silver_prefix_s3
  gold_prefix_s3       = var.gold_prefix_s3
  ddb_table_name       = module.dynamodb.table_name
  fixed_run            = var.fixed_run
  event_bus_name       = var.event_bus_name
  cognito_user_pool_id = var.cognito_user_pool_id
  dms_task_arn         = var.dms_task_arn
}

output "api_invoke_url" { value = module.apigw.invoke_url }


