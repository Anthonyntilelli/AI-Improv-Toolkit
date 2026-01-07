locals {
  my_ip   = "${chomp(data.http.my_ip.response_body)}/32"
  ssh_key = trimspace(file(var.absolute_path_to_ssh_key))
}

data "http" "my_ip" {
  url = "https://api.ipify.org"
}

resource "digitalocean_ssh_key" "default" {
  name       = var.ssh_key_name
  public_key = file(var.absolute_path_to_ssh_key)
}

resource "digitalocean_droplet" "analysis" {
  image     = var.gpu_droplet.image
  name      = "analysis"
  region    = var.gpu_droplet.region
  size      = var.gpu_droplet.size
  backups   = false
  ssh_keys  = [digitalocean_ssh_key.default.fingerprint]
  user_data = templatefile("cloud-init.yaml.tftpl", { "passwd_hash" = var.sysadmin_and_dev_password_hash, "ssh_key" = local.ssh_key })
}

# Firewall restricts inbound traffic but allows outbound traffic.
resource "digitalocean_firewall" "analysis" {
  name = "Show-firewall"

  droplet_ids = [digitalocean_droplet.analysis.id]
  dynamic "inbound_rule" {
    for_each = var.firewall_ingress_list
    content {
      protocol         = inbound_rule.value.protocol
      port_range       = try(inbound_rule.value.port, null)
      source_addresses = inbound_rule.value.local_ip ? concat(inbound_rule.value.ips_ciders, [local.my_ip]) : inbound_rule.value.ips_ciders
    }
  }
  outbound_rule {
    protocol              = "tcp"
    port_range            = "0"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "0"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

resource "cloudflare_dns_record" "example_dns_record" {
  count   = length(var.dns_record)
  zone_id = var.zone_id
  name    = var.dns_record[count.index]
  ttl     = 3600
  type    = "A"
  comment = "Service for ${var.dns_record[count.index]}"
  content = digitalocean_droplet.analysis.ipv4_address
  proxied = false
}
