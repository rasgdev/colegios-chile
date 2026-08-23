# ──────────────────────────────────────────────
# Firewalls
# ──────────────────────────────────────────────

resource "google_compute_firewall" "allow_http_https" {
  name    = "allow-http-https"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  target_tags   = ["web-server"]
  source_ranges = ["0.0.0.0/0"]
  description   = "Allow HTTP and HTTPS traffic"
}

resource "google_compute_firewall" "allow_ssh" {
  name    = "allow-ssh"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  target_tags   = ["web-server"]
  source_ranges = var.ssh_source_ranges
  description   = "Allow SSH traffic"
}

# ──────────────────────────────────────────────
# IAP + OS Login + IAM del service account de deploy
# ──────────────────────────────────────────────

resource "google_project_service" "iap" {
  project            = var.project_id
  service            = "iap.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_iam_member" "deploy_iap_tunnel" {
  project = var.project_id
  role    = "roles/iap.tunnelResourceAccessor"
  member  = "serviceAccount:${var.deploy_sa_email}"
}

resource "google_project_iam_member" "deploy_instance_admin" {
  project = var.project_id
  role    = "roles/compute.instanceAdmin.v1"
  member  = "serviceAccount:${var.deploy_sa_email}"
}

resource "google_project_iam_member" "deploy_service_account_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${var.deploy_sa_email}"
}

resource "google_project_iam_member" "tf_sa_service_account_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${var.tf_sa_email}"
}

resource "time_sleep" "iam_propagation" {
  depends_on = [
    google_project_iam_member.deploy_iap_tunnel,
    google_project_iam_member.deploy_service_account_user,
    google_project_iam_member.tf_sa_service_account_user,
    google_project_iam_member.deploy_instance_admin,
  ]

  create_duration = "60s"
}

# ──────────────────────────────────────────────
# IP estatica (para que la IP no cambie al reiniciar)
# ──────────────────────────────────────────────

resource "google_compute_address" "static_ip" {
  name   = "colegios-static-ip"
  region = var.region
}

# ──────────────────────────────────────────────
# VM principal
# ──────────────────────────────────────────────

resource "google_compute_instance" "colegios_server" {
  name         = "colegios-server"
  machine_type = var.machine_type
  zone         = var.zone

  depends_on = [time_sleep.iam_propagation]

  tags = ["web-server"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2404-lts-amd64"
      size  = var.boot_disk_size
      type  = "pd-standard"
    }
  }

  network_interface {
    network = "default"
    access_config {
      nat_ip = google_compute_address.static_ip.address
    }
  }

  metadata = {
    ssh-keys = "colegios:${var.ssh_public_key}"
    startup-script = templatefile("${path.module}/startup.sh", {
      repo_url    = var.repo_url
      repo_branch = var.repo_branch
      db_password = var.db_password
    })
  }

  service_account {
    scopes = ["cloud-platform"]
  }

  labels = {
    env        = "production"
    app        = "colegios-chile"
    managed-by = "terraform"
  }
}