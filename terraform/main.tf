terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    # You must create this bucket MANUALLY in AWS first!
    bucket         = "pyjaapp-terraform-state-backend"
    key            = "state/terraform.tfstate"
    region         = "eu-north-1" # Updated to match your actual bucket location
    use_lockfile   = true         # Modern terraform way, replaces dynamodb
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  name_prefix = "${var.app_name}-${var.environment}"
}

resource "random_password" "jwt_secret" {
  length  = 32
  special = false
}

# --- S3 ---
resource "aws_s3_bucket" "assets" {
  bucket = "${local.name_prefix}-assets"
}

# --- Lambda + API Gateway ---
resource "aws_iam_role" "lambda_exec" {
  name = "${local.name_prefix}-lambda-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_policy" "lambda_policy" {
  name = "${local.name_prefix}-lambda-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = ["s3:*"]
        Effect = "Allow"
        Resource = "${aws_s3_bucket.assets.arn}/*"
      },
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

resource "aws_lambda_function" "api" {
  function_name = "${local.name_prefix}-api"
  filename      = "../lambda_function.zip"
  source_code_hash = fileexists("../lambda_function.zip") ? filebase64sha256("../lambda_function.zip") : null
  handler       = "app.main.handler"
  runtime       = "python3.12"
  role          = aws_iam_role.lambda_exec.arn
  timeout       = 15

  environment {
    variables = {
      ENV              = var.environment
      S3_BUCKET_NAME   = aws_s3_bucket.assets.id
      DATABASE_URL     = var.supabase_db_url
      JWT_SECRET_KEY   = random_password.jwt_secret.result
      GOOGLE_CLIENT_ID = var.google_client_id
      RESEND_API_KEY   = var.resend_api_key
    }
  }
}

resource "aws_apigatewayv2_api" "lambda" {
  name          = "${local.name_prefix}-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_stage" "lambda" {
  api_id      = aws_apigatewayv2_api.lambda.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id             = aws_apigatewayv2_api.lambda.id
  integration_uri    = aws_lambda_function.api.invoke_arn
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
}

resource "aws_apigatewayv2_route" "lambda" {
  api_id    = aws_apigatewayv2_api.lambda.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "lambda_root" {
  api_id    = aws_apigatewayv2_api.lambda.id
  route_key = "ANY /"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.lambda.execution_arn}/*/*"
}

output "api_gateway_url" {
  value = aws_apigatewayv2_stage.lambda.invoke_url
}
