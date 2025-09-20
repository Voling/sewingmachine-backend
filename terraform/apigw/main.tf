data "aws_caller_identity" "this" {}

resource "aws_api_gateway_rest_api" "api" {
  name = "${var.project_name}-api"
  endpoint_configuration { types = ["REGIONAL"] }
  tags = var.tags
}

resource "aws_api_gateway_authorizer" "cognito" {
  name            = "cognito"
  rest_api_id     = aws_api_gateway_rest_api.api.id
  type            = "COGNITO_USER_POOLS"
  identity_source = "method.request.header.Authorization"
  provider_arns   = ["arn:aws:cognito-idp:${var.aws_region}:${data.aws_caller_identity.this.account_id}:userpool/${var.cognito_user_pool_id}"]
}

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

resource "aws_api_gateway_integration" "health" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_get.http_method
  integration_http_method = "POST"
  type = "AWS_PROXY"
  uri  = var.lambda_health_invoke_arn
}
resource "aws_api_gateway_integration" "run" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.run.id
  http_method = aws_api_gateway_method.run_post.http_method
  integration_http_method = "POST"
  type = "AWS_PROXY"
  uri  = var.lambda_run_invoke_arn
}
resource "aws_api_gateway_integration" "query" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.query.id
  http_method = aws_api_gateway_method.query_post.http_method
  integration_http_method = "POST"
  type = "AWS_PROXY"
  uri  = var.lambda_query_invoke_arn
}
resource "aws_api_gateway_integration" "schemas" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.schemas.id
  http_method = aws_api_gateway_method.schemas_get.http_method
  integration_http_method = "POST"
  type = "AWS_PROXY"
  uri  = var.lambda_schemas_invoke_arn
}

resource "aws_api_gateway_deployment" "this" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  triggers = { redeploy = sha1(join(",", [
    jsonencode(aws_api_gateway_integration.health),
    jsonencode(aws_api_gateway_integration.run),
    jsonencode(aws_api_gateway_integration.query),
    jsonencode(aws_api_gateway_integration.schemas)
  ])) }
  lifecycle { create_before_destroy = true }
  depends_on = [
    aws_api_gateway_integration.health,
    aws_api_gateway_integration.run,
    aws_api_gateway_integration.query,
    aws_api_gateway_integration.schemas
  ]
}

resource "aws_api_gateway_stage" "v1" {
  deployment_id = aws_api_gateway_deployment.this.id
  rest_api_id   = aws_api_gateway_rest_api.api.id
  stage_name    = "v1"
  tags          = var.tags
}

resource "aws_lambda_permission" "apigw_invoke" {
  for_each      = {
    health  = var.lambda_health_name
    run     = var.lambda_run_name
    query   = var.lambda_query_name
    schemas = var.lambda_schemas_name
  }
  statement_id  = "AllowAPIGatewayInvoke-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = each.value
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}

output "invoke_url" { value = aws_api_gateway_stage.v1.invoke_url }

