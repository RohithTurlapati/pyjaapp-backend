variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "app_name" {
  description = "Name of the application"
  type        = string
}

variable "environment" {
  description = "Deployment environment (e.g., dev, prod)"
  type        = string
}

variable "supabase_db_url" {
  description = "The database URL from Supabase"
  type        = string
  sensitive   = true
}

variable "google_client_id" {
  description = "Google Auth Client ID"
  type        = string
  sensitive   = true
}

variable "mail_username" {
  description = "Mail Username (e.g. Gmail address)"
  type        = string
  sensitive   = true
}

variable "mail_password" {
  description = "Mail Password (e.g. Gmail App Password)"
  type        = string
  sensitive   = true
}
