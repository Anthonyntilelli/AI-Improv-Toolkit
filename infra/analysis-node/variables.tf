variable "ssh_key_name" {
  description = "Name of ssh key to added to digital ocean"
  type = string
  nullable = false
}

variable "absolute_path_to_ssh_key" {
  description = "Absolute value to public ssh key on local machine."
  type = string
  nullable = false
  validation {
    condition     = fileexists(var.config_path)
    error_message = "The file specified by config_path does not exist."
  }
  validation {
    condition     = endswith(var.ssh_public_key_path, ".pub")
    error_message = "ssh_public_key_path must end with .pub."
  }
}

variable "firewall_ingress_list" {
  description = "List of ingress ports to allow on digital ocean firewall,"
  type = list(object({
    service = string,
    ips_ciders = list(strings), # Can be ipv4 and IPv6
    local_ip = bool,
    protocol = string,
    port = optional(string)
  }))
  nullable = false

  validation {
    condition = alltrue([
      for r in var.firewall_ingress_list : contains(["tcp", "udp", "icmp"], lower(trimspace(r.protocol)))])
    error_message = "Each entry 'protocol' must be one of: tcp, udp, icmp."
  }
}

variable "zone_id" {
  description = "Cloudflare DNS Zone ID"
  nullable = false
  type = string
  sensitive = true
}

variable "dns_record" {
  description = "list of servers dns records to create, currently all map to the one droplet"
  nullable = false
  type = list(string)
}

variable "gpu_droplet" {
  description = "GPU droplet configuration"
  type = object({
    image   = string
    region  = string
    size    = string
  })
  nullable = false
}
