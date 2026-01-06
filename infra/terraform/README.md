# Analysis Node

Terraform build script for the analysis node. This config uses digital ocean and cloudflare for its set up.

## Pre-requisites

- Create a `terraform.tfvars` from example file `terraform.tfvars.example`.
- Set and export the environmental variable `DIGITALOCEAN_TOKEN` with a digital ocean api key.
  - Scope needed are droplet, firewall, ssh_key, tag (additional scopes may be added.)
- Set and export the environmental variable `CLOUDFLARE_API_TOKEN` with a cloudflare api Token.
  - API token only needs to "edit zone DNS".
- Set and export the environmental variable `TF_VAR_sysadmin_and_dev_password_hash` with hash password from `mkpasswd --method=SHA-512 --rounds=500000`

## Deploy

1. `terraform init`
2. `terraform plan`
3. `terraform apply`

## Digital Ocean GPU Sizes versions (12/2025)

|Slug               |         Description                   |    Memory  |    VCPUs |    Disk |    Price Monthly |    Price Hourly |
|-------------------|---------------------------------------|------------|----------|---------|------------------|-----------------|
|gpu-4000adax1-20gb |         RTX 4000 Ada GPU Droplet - 1X |    32768   |    8     |    500  |    565.44        |    0.760000     |
|gpu-l40sx1-48gb    |         L40S GPU Droplet - 1X         |    65536   |    8     |    500  |    1168.08       |    1.570000     |
|gpu-6000adax1-48gb |         RTX 6000 Ada GPU Droplet - 1X |    65536   |    8     |    500  |    1168.08       |    1.570000     |
|gpu-mi300x1-192gb  |         AMD MI300X - 1X               |    245760  |    20    |    720  |    1480.56       |    1.990000     |
|gpu-h100x1-80gb    |         H100 GPU - 1X                 |    245760  |    20    |    720  |    2522.16       |    3.390000     |
|gpu-h200x1-141gb   |         Nvidia H200 - 1X              |    245760  |    24    |    720  |    2559.36       |    3.440000     |
|gpu-mi300x8-1536gb |         AMD MI300X - 8X               |    1966080 |    160   |    2046 |    11844.48      |    15.920000    |
|gpu-h100x8-640gb   |         H100 GPU - 8X                 |    1966080 |    160   |    2046 |    17796.48      |    23.920000    |
|gpu-h200x8-1128gb  |         Nvidia H200 - 8X              |    1966080 |    192   |    2046 |    20474.88      |    27.520000    |

## Digital Ocean GPU Image Version (12/2025)

|ID        |   Name                           |           Type  |         Distribution |  Slug                          |               Public |   Min Disk  |
|----------|----------------------------------|-----------------|----------------------|--------------------------------|----------------------|-------------|
|203838208 |   AMD AI/ML Ready                |            base |         Ubuntu       |   gpu-amd-base                 |                true  |    30       |
|203838782 |   NVIDIA AI/ML Ready             |            base |         Ubuntu       |   gpu-h100x1-base              |                true  |    30       |
|203839248 |   NVIDIA AI/ML Ready with NVLink |            base |         Ubuntu       |   gpu-h100x8-base              |                true  |    30       |

## Notes

- Make sure the selected GPU size is compatible with the selected image.
