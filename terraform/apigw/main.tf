data "aws_caller_identity" "this" {}

locals {
  cors_allow_headers = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
  cors_allow_origin  = format("'%s'", var.allowed_origin)
  cors_allow_methods = {
    health      = "'GET,OPTIONS'"
    run         = "'OPTIONS,POST'"
    query       = "'OPTIONS,POST'"
    schemas     = "'GET,OPTIONS'"
    materialize = "'OPTIONS,POST'"
  }
  create_custom_domain = var.custom_domain_name != "" && var.certificate_arn != ""
  custom_domain_is_edge = upper(var.custom_domain_endpoint_type) == "EDGE"
}

resource "aws_api_gateway_account" "this" {
  count               = var.cloudwatch_role_arn == "" ? 0 : 1
  cloudwatch_role_arn = var.cloudwatch_role_arn
}

resource "aws_api_gateway_rest_api" "api" {
  name           = var.rest_api_name
  api_key_source = "HEADER"
  endpoint_configuration { types = ["REGIONAL"] }
  disable_execute_api_endpoint = false
  tags                         = var.tags
}

resource "aws_api_gateway_authorizer" "cognito" {
  name            = "CognitoAuth"
  rest_api_id     = aws_api_gateway_rest_api.api.id
  type            = "COGNITO_USER_POOLS"
  identity_source = "method.request.header.Authorization"
  provider_arns = [
    format(
      "arn:aws:cognito-idp:%s:%s:userpool/%s",
      var.aws_region,
      data.aws_caller_identity.this.account_id,
      var.cognito_user_pool_id
    )
  ]
}

# API resources
resource "aws_api_gateway_resource" "health" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "health"
}

resource "aws_api_gateway_resource" "run" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "run"
}

resource "aws_api_gateway_resource" "query" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "query"
}

resource "aws_api_gateway_resource" "schemas" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "schemas"
}

resource "aws_api_gateway_resource" "materialize" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "materialize"
}

# Primary methods
resource "aws_api_gateway_method" "health_get" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.health.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_method" "run_post" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.run.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_method" "query_post" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.query.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_method" "schemas_get" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.schemas.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_method" "materialize_post" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.materialize.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

# Method responses
resource "aws_api_gateway_method_response" "health_200" {
  rest_api_id     = aws_api_gateway_rest_api.api.id
  resource_id     = aws_api_gateway_resource.health.id
  http_method     = aws_api_gateway_method.health_get.http_method
  status_code     = "200"
  response_models = { "application/json" = "Empty" }
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = false
  }
  lifecycle {
    ignore_changes = [response_models]
  }
}

resource "aws_api_gateway_method_response" "run_200" {
  rest_api_id     = aws_api_gateway_rest_api.api.id
  resource_id     = aws_api_gateway_resource.run.id
  http_method     = aws_api_gateway_method.run_post.http_method
  status_code     = "200"
  response_models = { "application/json" = "Empty" }
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = false
  }
  lifecycle {
    ignore_changes = [response_models]
  }
}

resource "aws_api_gateway_method_response" "query_200" {
  rest_api_id     = aws_api_gateway_rest_api.api.id
  resource_id     = aws_api_gateway_resource.query.id
  http_method     = aws_api_gateway_method.query_post.http_method
  status_code     = "200"
  response_models = { "application/json" = "Empty" }
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = false
  }
  lifecycle {
    ignore_changes = [response_models]
  }
}

resource "aws_api_gateway_method_response" "schemas_200" {
  rest_api_id     = aws_api_gateway_rest_api.api.id
  resource_id     = aws_api_gateway_resource.schemas.id
  http_method     = aws_api_gateway_method.schemas_get.http_method
  status_code     = "200"
  response_models = { "application/json" = "Empty" }
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = false
  }
  lifecycle {
    ignore_changes = [response_models]
  }
}

resource "aws_api_gateway_method_response" "materialize_200" {
  rest_api_id     = aws_api_gateway_rest_api.api.id
  resource_id     = aws_api_gateway_resource.materialize.id
  http_method     = aws_api_gateway_method.materialize_post.http_method
  status_code     = "200"
  response_models = { "application/json" = "Empty" }
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = false
  }
  lifecycle {
    ignore_changes = [response_models]
  }
}

# Integrations
resource "aws_api_gateway_integration" "health" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.health.id
  http_method             = aws_api_gateway_method.health_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri = var.lambda_health_invoke_arn
}

resource "aws_api_gateway_integration" "run" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.run.id
  http_method             = aws_api_gateway_method.run_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri = var.lambda_run_invoke_arn
}

resource "aws_api_gateway_integration" "query" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.query.id
  http_method             = aws_api_gateway_method.query_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri = var.lambda_query_invoke_arn
}

resource "aws_api_gateway_integration" "schemas" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.schemas.id
  http_method             = aws_api_gateway_method.schemas_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri = var.lambda_schemas_invoke_arn
}

resource "aws_api_gateway_integration" "materialize" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.materialize.id
  http_method             = aws_api_gateway_method.materialize_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri = var.lambda_materialize_invoke_arn
}

# OPTIONS methods
resource "aws_api_gateway_method" "health_options" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.health.id
  http_method   = "OPTIONS"
  authorization = "NONE"
  request_parameters = {
    "method.request.header.Origin" = false
  }
}

resource "aws_api_gateway_method" "run_options" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.run.id
  http_method   = "OPTIONS"
  authorization = "NONE"
  request_parameters = {
    "method.request.header.Origin" = false
  }
}

resource "aws_api_gateway_method" "query_options" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.query.id
  http_method   = "OPTIONS"
  authorization = "NONE"
  request_parameters = {
    "method.request.header.Origin" = false
  }
}

resource "aws_api_gateway_method" "schemas_options" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.schemas.id
  http_method   = "OPTIONS"
  authorization = "NONE"
  request_parameters = {
    "method.request.header.Origin" = false
  }
}

resource "aws_api_gateway_method" "materialize_options" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.materialize.id
  http_method   = "OPTIONS"
  authorization = "NONE"
  request_parameters = {
    "method.request.header.Origin" = false
  }
}

# OPTIONS responses
resource "aws_api_gateway_method_response" "health_options_200" {
  rest_api_id     = aws_api_gateway_rest_api.api.id
  resource_id     = aws_api_gateway_resource.health.id
  http_method     = aws_api_gateway_method.health_options.http_method
  status_code     = "200"
  response_models = { "application/json" = "Empty" }
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = false
    "method.response.header.Access-Control-Allow-Methods" = false
    "method.response.header.Access-Control-Allow-Origin"  = false
  }
  lifecycle {
    ignore_changes = [response_models]
  }
}

resource "aws_api_gateway_method_response" "run_options_200" {
  rest_api_id     = aws_api_gateway_rest_api.api.id
  resource_id     = aws_api_gateway_resource.run.id
  http_method     = aws_api_gateway_method.run_options.http_method
  status_code     = "200"
  response_models = { "application/json" = "Empty" }
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = false
    "method.response.header.Access-Control-Allow-Methods" = false
    "method.response.header.Access-Control-Allow-Origin"  = false
  }
  lifecycle {
    ignore_changes = [response_models]
  }
}

resource "aws_api_gateway_method_response" "query_options_200" {
  rest_api_id     = aws_api_gateway_rest_api.api.id
  resource_id     = aws_api_gateway_resource.query.id
  http_method     = aws_api_gateway_method.query_options.http_method
  status_code     = "200"
  response_models = { "application/json" = "Empty" }
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = false
    "method.response.header.Access-Control-Allow-Methods" = false
    "method.response.header.Access-Control-Allow-Origin"  = false
  }
  lifecycle {
    ignore_changes = [response_models]
  }
}

resource "aws_api_gateway_method_response" "schemas_options_200" {
  rest_api_id     = aws_api_gateway_rest_api.api.id
  resource_id     = aws_api_gateway_resource.schemas.id
  http_method     = aws_api_gateway_method.schemas_options.http_method
  status_code     = "200"
  response_models = { "application/json" = "Empty" }
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = false
    "method.response.header.Access-Control-Allow-Methods" = false
    "method.response.header.Access-Control-Allow-Origin"  = false
  }
  lifecycle {
    ignore_changes = [response_models]
  }
}

resource "aws_api_gateway_method_response" "materialize_options_200" {
  rest_api_id     = aws_api_gateway_rest_api.api.id
  resource_id     = aws_api_gateway_resource.materialize.id
  http_method     = aws_api_gateway_method.materialize_options.http_method
  status_code     = "200"
  response_models = { "application/json" = "Empty" }
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = false
    "method.response.header.Access-Control-Allow-Methods" = false
    "method.response.header.Access-Control-Allow-Origin"  = false
  }
  lifecycle {
    ignore_changes = [response_models]
  }
}

# OPTIONS integrations
resource "aws_api_gateway_integration" "health_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_options.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.lambda_health_invoke_arn
}

resource "aws_api_gateway_integration" "run_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.run.id
  http_method = aws_api_gateway_method.run_options.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.lambda_run_invoke_arn
}

resource "aws_api_gateway_integration" "query_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.query.id
  http_method = aws_api_gateway_method.query_options.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.lambda_query_invoke_arn
}

resource "aws_api_gateway_integration" "schemas_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.schemas.id
  http_method = aws_api_gateway_method.schemas_options.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.lambda_schemas_invoke_arn
}

resource "aws_api_gateway_integration" "materialize_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.materialize.id
  http_method = aws_api_gateway_method.materialize_options.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.lambda_materialize_invoke_arn
}

# OPTIONS integration responses
// Integration responses are not used with Lambda proxy integrations for OPTIONS

resource "aws_api_gateway_deployment" "this" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  triggers = {
    redeploy = sha1(join(",", [
      jsonencode(aws_api_gateway_integration.health),
      jsonencode(aws_api_gateway_integration.run),
      jsonencode(aws_api_gateway_integration.query),
      jsonencode(aws_api_gateway_integration.schemas),
      jsonencode(aws_api_gateway_integration.materialize),
      jsonencode(aws_api_gateway_integration.health_options),
      jsonencode(aws_api_gateway_integration.run_options),
      jsonencode(aws_api_gateway_integration.query_options),
      jsonencode(aws_api_gateway_integration.schemas_options),
      jsonencode(aws_api_gateway_integration.materialize_options)
    ]))
  }
  lifecycle { create_before_destroy = true }
  depends_on = [
    aws_api_gateway_integration.health,
    aws_api_gateway_integration.run,
    aws_api_gateway_integration.query,
    aws_api_gateway_integration.schemas,
    aws_api_gateway_integration.materialize,
    aws_api_gateway_integration.health_options,
    aws_api_gateway_integration.run_options,
    aws_api_gateway_integration.query_options,
    aws_api_gateway_integration.schemas_options,
    aws_api_gateway_integration.materialize_options
  ]
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.this.id
  rest_api_id   = aws_api_gateway_rest_api.api.id
  stage_name    = "prod"
  tags          = var.tags
}

resource "aws_api_gateway_method_settings" "all" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  stage_name  = aws_api_gateway_stage.prod.stage_name
  method_path = "*/*"

  settings {
    metrics_enabled                            = true
    logging_level                              = "INFO"
    data_trace_enabled                         = true
    throttling_burst_limit                     = 5000
    throttling_rate_limit                      = 10000
    caching_enabled                            = false
    cache_data_encrypted                       = false
    cache_ttl_in_seconds                       = 300
    require_authorization_for_cache_control    = true
    unauthorized_cache_control_header_strategy = "SUCCEED_WITH_RESPONSE_HEADER"
  }
}

# Lambda permissions
resource "aws_lambda_permission" "health" {
  statement_id  = "apigw-sewingmachine-health-31866"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_health_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = format("%s/*/*/*", aws_api_gateway_rest_api.api.execution_arn)
}

resource "aws_lambda_permission" "run" {
  statement_id  = "apigw-sewingmachine-run-25454"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_run_name
  principal     = "apigateway.amazonaws.com"
  # Allow API Gateway to invoke for any method (POST, OPTIONS) on any resource
  source_arn    = format("%s/*/*/*", aws_api_gateway_rest_api.api.execution_arn)
}

resource "aws_lambda_permission" "query" {
  statement_id  = "apigw-sewingmachine-query-31866"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_query_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = format("%s/*/*/*", aws_api_gateway_rest_api.api.execution_arn)
}

resource "aws_lambda_permission" "schemas" {
  statement_id  = "apigw-sewingmachine-schemas-31866"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_schemas_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = format("%s/*/*/*", aws_api_gateway_rest_api.api.execution_arn)
}

resource "aws_lambda_permission" "materialize" {
  statement_id  = "apigw-sewingmachine-materialize-31866"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_materialize_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = format("%s/*/*/*", aws_api_gateway_rest_api.api.execution_arn)
}

# Optional custom domain
resource "aws_api_gateway_domain_name" "custom" {
  count = local.create_custom_domain ? 1 : 0

  domain_name              = var.custom_domain_name
  certificate_arn          = local.custom_domain_is_edge ? var.certificate_arn : null
  regional_certificate_arn = local.custom_domain_is_edge ? null : var.certificate_arn
  endpoint_configuration { types = [var.custom_domain_endpoint_type] }
  security_policy = "TLS_1_2"
  tags            = var.tags
}

# Root base path mapping so that https://api.<domain>/* maps to the API stage.
resource "aws_api_gateway_base_path_mapping" "root" {
  count       = local.create_custom_domain ? 1 : 0
  api_id      = aws_api_gateway_rest_api.api.id
  stage_name  = aws_api_gateway_stage.prod.stage_name
  domain_name = aws_api_gateway_domain_name.custom[count.index].domain_name
}

output "invoke_url" {
  value = aws_api_gateway_stage.prod.invoke_url
}

output "custom_domain_regional_domain" {
  value = length(aws_api_gateway_domain_name.custom) == 0 ? null : aws_api_gateway_domain_name.custom[0].regional_domain_name
}

output "custom_domain_regional_zone_id" {
  value = length(aws_api_gateway_domain_name.custom) == 0 ? null : aws_api_gateway_domain_name.custom[0].regional_zone_id
}
