variable "aws_region" {
  type    = string
  default = "us-west-1"
}

variable "project_name" {
  type    = string
  default = "sewingmachine"
}

variable "rest_api_name" {
  type    = string
  default = "SewingMachine"
}

variable "apigw_cloudwatch_role_arn" {
  type    = string
  default = ""
}

variable "ddb_table_name" {
  type    = string
  default = "sewingmachine-cooldowns"
}

variable "bronze_prefix_s3" {
  type    = string
  default = "s3://fabric-aws-poc/bronze/"
}

variable "silver_prefix_s3" {
  type    = string
  default = "s3://fabric-aws-poc/silver/"
}

variable "gold_prefix_s3" {
  type    = string
  default = "s3://fabric-aws-poc/gold/"
}

variable "athena_output" {
  type    = string
  default = "s3://fabric-aws-poc/_dq/athena-results/"
}

variable "athena_wg" {
  type    = string
  default = "primary"
}

variable "athena_catalog" {
  type    = string
  default = "AwsDataCatalog"
}

variable "allowed_origin" {
  type    = string
  default = "https://awssewingmachine.com,http://localhost:5173"
}

variable "fixed_run" {
  type    = string
  default = "2025-08-13"
}

variable "event_bus_name" {
  type    = string
  default = "default"
}

variable "cognito_user_pool_id" {
  type    = string
  default = "us-west-1_0nv0MHKcd"
}

variable "custom_domain_name" {
  type    = string
  default = "awssewingmachine.com"
}

variable "certificate_arn" {
  type = string
}

variable "custom_domain_endpoint_type" {
  type    = string
  default = "REGIONAL"
}

variable "dms_task_arn" {
  type = string
}

variable "default_tags" {
  type    = map(string)
  default = {}
}
