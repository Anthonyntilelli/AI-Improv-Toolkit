terraform {
  required_providers {
    digitalocean = {
      source = "digitalocean/digitalocean"
      version = "2.72.0"
    }
    cloudflare = {
      source = "cloudflare/cloudflare"
      version = "5.15.0"
    }
    required_version = ">= 1.14.3"
  }
  backend "local" {
    path = "./infra/analysis-pc/terraform.tfstate"
  }
}

provider "digitalocean" {}
provider "cloudflare" {}


