variable "project_name" { type = string }
variable "aws_region" { type = string }
variable "cognito_user_pool_id" { type = string }
variable "tags" { type = map(string) }

variable "lambda_health_invoke_arn" { type = string }
variable "lambda_run_invoke_arn"    { type = string }
variable "lambda_query_invoke_arn"  { type = string }
variable "lambda_schemas_invoke_arn"{ type = string }

variable "lambda_health_name"  { type = string }
variable "lambda_run_name"     { type = string }
variable "lambda_query_name"   { type = string }
variable "lambda_schemas_name" { type = string }


