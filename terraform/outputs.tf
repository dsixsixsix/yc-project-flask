output "app_url" {
  description = "URL to access the application"
  value       = "http://localhost:8080"
}

output "minio_console_url" {
  description = "URL to access MinIO console"
  value       = "http://localhost:9001"
}

output "minio_api_url" {
  description = "URL to access MinIO API"
  value       = "http://localhost:9000"
}

output "networks" {
  description = "Created Docker networks (VPC)"
  value = {
    frontend = docker_network.frontend.name
    backend  = docker_network.backend.name
    storage  = docker_network.storage.name
  }
}

output "containers" {
  description = "Created containers"
  value = {
    nginx = docker_container.nginx.name
    app   = docker_container.app.name
    minio = docker_container.minio.name
  }
}
