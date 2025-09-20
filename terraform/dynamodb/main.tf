resource "aws_dynamodb_table" "cooldowns" {
  name         = var.ddb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "resource"

  attribute {
    name = "resource"
    type = "S"
  }

  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }

  tags = var.tags
}

output "table_name" { value = aws_dynamodb_table.cooldowns.name }
output "table_arn"  { value = aws_dynamodb_table.cooldowns.arn }

