variable "project_name" { type = string }
variable "rest_api_name" { type = string }
variable "aws_region" { type = string }
variable "allowed_origin" { type = string }
variable "cloudwatch_role_arn" {
  type    = string
  default = ""
}
variable "cognito_user_pool_id" { type = string }
variable "tags" { type = map(string) }
variable "custom_domain_name" { type = string }
variable "certificate_arn" { type = string }
variable "custom_domain_endpoint_type" {
  type    = string
  default = "REGIONAL"
}

variable "lambda_health_invoke_arn" { type = string }
variable "lambda_run_invoke_arn" { type = string }
variable "lambda_query_invoke_arn" { type = string }
variable "lambda_schemas_invoke_arn" { type = string }
variable "lambda_materialize_invoke_arn" { type = string }

variable "lambda_health_name" { type = string }
variable "lambda_run_name" { type = string }
variable "lambda_query_name" { type = string }
variable "lambda_schemas_name" { type = string }
variable "lambda_materialize_name" { type = string }

