variable "project_id" {
  description = "ID del proyecto GCP"
  type        = string
}

variable "region" {
  description = "Region GCP (debe ser us-west1, us-central1 o us-east1 para free tier)"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "Zona GCP (debe estar dentro de la region free tier)"
  type        = string
  default     = "us-central1-a"
}

variable "machine_type" {
  description = "Tipo de VM (free tier: e2-micro)"
  type        = string
  default     = "e2-micro"
}

variable "boot_disk_size" {
  description = "Tamano del disco de arranque en GB (free tier: max 30 GB standard)"
  type        = number
  default     = 20
}

variable "repo_url" {
  description = "URL del repositorio Git a clonar"
  type        = string
  default     = "https://github.com/rasgdev/colegios-chile.git"
}

variable "repo_branch" {
  description = "Branch del repositorio a desplegar"
  type        = string
  default     = "main"
}

variable "db_password" {
  description = "Password para el usuario de PostgreSQL"
  type        = string
  sensitive   = true
  default     = "colegios"
}

variable "deploy_sa_email" {
  description = "Email del service account que usa GitHub Actions (WIF) para deploy"
  type        = string
}

variable "ssh_source_ranges" {
  description = "Rangos CIDR permitidos para SSH directo. Con IAP puede quedar [] (cerrado)"
  type        = list(string)
  default     = []
}