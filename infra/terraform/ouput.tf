output "droplet_ip" {
  value = digitalocean_droplet.analysis.ipv4_address
}
output "droplet_hourly_price" {
  value = digitalocean_droplet.analysis.price_hourly
}
