terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

# ========== Volumes ==========

resource "docker_volume" "minio_data" {
  name = "ycproject_minio-data"
}

# ========== Networks (VPC) ==========

# Публичная подсеть для балансировщика
resource "docker_network" "frontend" {
  name = "ycproject_frontend-network"
  ipam_config {
    subnet = "172.20.0.0/24"
    gateway = "172.20.0.1"
  }
}

# Внутренняя подсеть для backend
resource "docker_network" "backend" {
  name = "ycproject_backend-network"
  ipam_config {
    subnet = "172.21.0.0/24"
    gateway = "172.21.0.1"
  }
}

# Подсеть для storage
resource "docker_network" "storage" {
  name = "ycproject_storage-network"
  ipam_config {
    subnet = "172.22.0.0/24"
    gateway = "172.22.0.1"
  }
}

# ========== Images ==========

resource "docker_image" "app" {
  name = "ycproject-app:latest"
  build {
    context = ".."
    dockerfile = "Dockerfile"
  }
}

resource "docker_image" "nginx" {
  name = "nginx:stable-alpine"
}

resource "docker_image" "minio" {
  name = "minio/minio:latest"
}

# ========== Containers ==========

# MinIO Object Storage
resource "docker_container" "minio" {
  name  = "ycproject-minio"
  image = docker_image.minio.image_id

  command = ["server", "/data", "--console-address", ":9001"]

  env = [
    "MINIO_ROOT_USER=${var.minio_root_user}",
    "MINIO_ROOT_PASSWORD=${var.minio_root_password}"
  ]

  ports {
    internal = 9000
    external = 9000
  }

  ports {
    internal = 9001
    external = 9001
  }

  volumes {
    volume_name    = docker_volume.minio_data.name
    container_path = "/data"
  }

  networks_advanced {
    name = docker_network.backend.name
  }

  networks_advanced {
    name = docker_network.storage.name
  }

  restart = "unless-stopped"
}

# Flask Application
resource "docker_container" "app" {
  name  = "ycproject-app"
  image = docker_image.app.image_id

  env = [
    "DATABASE_URL=${var.database_url}",
    "PORT=7777",
    "S3_ENDPOINT_URL=http://minio:9000",
    "S3_PUBLIC_ENDPOINT=http://localhost:9000",
    "S3_BUCKET=${var.s3_bucket}",
    "S3_REGION=${var.s3_region}",
    "S3_ACCESS_KEY=${var.minio_root_user}",
    "S3_SECRET_KEY=${var.minio_root_password}",
    "SECRET_KEY=${var.secret_key}",
    "LOG_LEVEL=INFO"
  ]

  networks_advanced {
    name = docker_network.backend.name
  }

  depends_on = [docker_container.minio]

  restart = "unless-stopped"
}

# Nginx Load Balancer
resource "docker_container" "nginx" {
  name  = "ycproject-nginx"
  image = docker_image.nginx.image_id

  ports {
    internal = 80
    external = 8080
  }

  volumes {
    host_path      = abspath("${path.cwd}/../nginx.conf")
    container_path = "/etc/nginx/conf.d/default.conf"
    read_only      = true
  }

  networks_advanced {
    name = docker_network.frontend.name
  }

  networks_advanced {
    name = docker_network.backend.name
  }

  depends_on = [docker_container.app]

  restart = "unless-stopped"
}
