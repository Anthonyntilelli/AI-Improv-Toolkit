locals {
  my_ip = "${chomp(data.http.my_ip.response_body)}/32"
  user_data = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    sysadmin_and_dev_password_hash = var.sysadmin_and_dev_password_hash
  })
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
  user_data = local.user_data
  ssh_keys  = [digitalocean_ssh_key.default.fingerprint]
}

resource "digitalocean_firewall" "analysis" {
  name = "Show_firewall"

  droplet_ids = [digitalocean_droplet.analysis.id]
  dynamic "inbound_rule" {
    for_each = var.firewall_ingress_list
    content {
      protocol         = inbound_rule.value.protocol
      port_range       = try(inbound_rule.value.port, null)
      source_addresses = inbound_rule.value.local_ip ? concat(inbound_rule.value.ips_ciders, [local.my_ip]) : inbound_rule.value.ips_ciders
    }
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
  settings = {
    ipv4_only = true
  }
}

output "path_module" {
  value = path.module
}
