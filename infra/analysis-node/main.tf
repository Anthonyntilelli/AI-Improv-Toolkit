/*
Create ssh key in Digital ocean
Create firewall with rules
Create GPU droplet and run cloud-init
Take ip address and create dns entries for nats, vision, hearing
*/

resource "digitalocean_ssh_key" "default" {
  name       = var.ssh_key_name
  public_key = file(var.absolute_path_to_ssh_key)
}

resource "digitalocean_droplet" "analysis" {
 # TODO
}

resource "digitalocean_firewall" "web" {
  name = "Show_firewall"

  droplet_ids = [digitalocean_droplet.analysis.id]

  # SSHD
  inbound_rule {
    protocol         = "tcp"
    port_range       = "8022"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Nats Clients
  inbound_rule {
    protocol         = "tcp"
    port_range       = "4222"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Nat HTTP management port for information reporting.
  inbound_rule {
    protocol         = "tcp"
    port_range       = "8222"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # TODO
  # ICMP
  # Hearing
  # Vision
}
