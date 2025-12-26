# Analysis Node

Terraform build script for the analysis node. This config uses digital ocean and cloudflare for its set up.

## Prerequisites

- Create a `terraform.tfvars` from example file `terraform.tfvars.example`.
- Set and export the environmental variable `DIGITALOCEAN_TOKEN` with a digital ocean api key.
    - Scope needed are droplet, firewall, ssh_key, tag
- Set and export the environmental variable `CLOUDFLARE_API_TOKEN` with a cloudflare api Token.
    - API token only needs to "edit zone DNS".

## Deploy

1. `terraform init`
2. `terraform plan`
3. `terraform apply`
