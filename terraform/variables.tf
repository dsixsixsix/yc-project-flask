variable "database_url" {
  description = "Database connection URL"
  type        = string
  default     = "sqlite:///app.db"
}

variable "s3_bucket" {
  description = "S3 bucket name for MinIO"
  type        = string
  default     = "demo-bucket"
}

variable "s3_region" {
  description = "S3 region"
  type        = string
  default     = "us-east-1"
}

variable "minio_root_user" {
  description = "MinIO root user"
  type        = string
  default     = "minioadmin"
  sensitive   = true
}

variable "minio_root_password" {
  description = "MinIO root password"
  type        = string
  default     = "minioadmin"
  sensitive   = true
}

variable "secret_key" {
  description = "Secret key for JWT tokens"
  type        = string
  default     = "dev-secret-key-change-in-production"
  sensitive   = true
}
