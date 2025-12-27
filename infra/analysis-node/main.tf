locals {
  my_ip = "${chomp(data.http.my_ip.response_body)}/32"
}

data "http" "my_ip" {
  url = "https://api.ipify.org"
}

resource "digitalocean_ssh_key" "default" {
  name       = var.ssh_key_name
  public_key = file(var.absolute_path_to_ssh_key)
}

# TODO Create GPU droplet and run cloud-init
resource "digitalocean_droplet" "analysis" {
  image   = "ubuntu-20-04-x64"
  name    = "analysis"
  region  = "nyc2"
  size    = "s-1vcpu-1gb"
  backups = false
  user_data = file("${path.module}/cloud-init.yaml")
}

resource "digitalocean_firewall" "analysis" {
  name = "Show_firewall"

  droplet_ids = [digitalocean_droplet.analysis.id]
  dynamic "inbound_rule" {
    for_each = var.firewall_ingress_list
    content {
      protocol         = inbound_rule.value[protocol]
      port_range       =  inbound_rule.value[port]
      source_addresses = inbound_rule.value[local_ip] ? concat(inbound_rule.value[ips_ciders], [local.my_ip]) : local.my_ip
    }
  }
}

resource "cloudflare_dns_record" "example_dns_record" {
  count = length(var.dns_record)
  zone_id = var.zone_id
  name = var.dns_record[count.index]
  ttl = 3600
  type = "A"
  comment = "Service for ${var.dns_record[count.index]}"
  content = digitalocean_droplet.analysis.ipv4_address
  proxied = false
  settings = {
    ipv4_only = true
  }
}
