output "instance_name" {
  description = "Nombre de la instancia VM"
  value       = google_compute_instance.colegios_server.name
}

output "instance_ip" {
  description = "IP publica de la instancia"
  value       = google_compute_address.static_ip.address
}

output "instance_zone" {
  description = "Zona de la instancia"
  value       = google_compute_instance.colegios_server.zone
}

output "ssh_command" {
  description = "Comando SSH para conectarse a la VM"
  value       = "gcloud compute ssh ${google_compute_instance.colegios_server.name} --zone=${var.zone}"
}

output "app_url" {
  description = "URL de la aplicacion"
  value       = "http://${google_compute_address.static_ip.address}"
}