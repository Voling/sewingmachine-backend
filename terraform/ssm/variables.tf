variable "allowed_origin" { type = string }
variable "athena_output" { type = string }
variable "athena_wg" { type = string }
variable "athena_catalog" { type = string }
variable "bronze_prefix_s3" { type = string }
variable "silver_prefix_s3" { type = string }
variable "gold_prefix_s3" { type = string }
variable "ddb_table_name" { type = string }
variable "fixed_run" { type = string }
variable "event_bus_name" { type = string }
variable "cognito_user_pool_id" { type = string }
variable "dms_task_arn" { type = string }

