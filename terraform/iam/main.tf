data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_role" {
  name               = "${var.project_name}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "basic_exec" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "lambda_permissions" {
  statement {
    effect   = "Allow"
    actions  = ["dynamodb:*"]
    resources = [var.ddb_table_arn]
  }
  statement {
    effect   = "Allow"
    actions  = ["lambda:InvokeFunction","lambda:AddPermission"]
    resources = ["*"]
  }
  statement {
    effect   = "Allow"
    actions  = ["s3:GetObject","s3:PutObject","s3:ListBucket"]
    resources = ["*"]
  }
  statement {
    effect   = "Allow"
    actions  = ["athena:StartQueryExecution","athena:GetQueryExecution","athena:GetQueryResults"]
    resources = ["*"]
  }
  statement {
    effect   = "Allow"
    actions  = ["events:PutRule","events:PutTargets","events:RemoveTargets","events:DeleteRule"]
    resources = ["*"]
  }
  statement {
    effect   = "Allow"
    actions  = ["dms:StartReplicationTask"]
    resources = [var.dms_task_arn]
  }
  statement {
    effect   = "Allow"
    actions  = ["glue:GetDatabases","glue:GetTables"]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "lambda_inline" {
  name   = "${var.project_name}-lambda-inline"
  policy = data.aws_iam_policy_document.lambda_permissions.json
}

resource "aws_iam_role_policy_attachment" "lambda_inline_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_inline.arn
}

output "lambda_role_arn" { value = aws_iam_role.lambda_role.arn }

