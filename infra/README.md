# Infrastructure Setup

This directory contain all the tools and configurations required to set up and manage the infrastructure for the AI Improv Toolkit project. It include a terraform configuration for provisioning cloud resources, ansible playbooks for configuring servers, and scripts for automating deployment tasks.

The objective of this folder is to become as show ready as possible with minimal manual intervention. The goal is to enable anyone on the team to spin up a new instance of the infrastructure quickly and reliably.

## Contents

- `terraform/`: Contains terraform configuration files for provisioning cloud resources.
- `ansible/`: Contains ansible playbooks and roles for configuring servers.
- `scripts/`: Contains various scripts for automating deployment and management tasks.
- `README.md`: This file, providing an overview of the infrastructure setup.
- `manual_setup.md`: Instructions for any manual setup steps that are required.

## Installation

Note: Many of these items may already be installed if you are using the development environment setup instructions.
To set up the infrastructure, you will need to have the following tools installed on your local machine:

- [Terraform](https://www.terraform.io/downloads)
- [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)
- Install `whois` package for `mkpasswd`

## Getting Started

To get started with setting up the infrastructure, follow these steps:

1. Follow installation instructions above.
2. (Optional) Use `../secrets/infra.env.sh.example` as a guide to populate and store environmental variables for infra.
    - Remove the `.example` on the end to ensure its ignored by git and detect-secrets.
3. Run `scripts/pki_manager.sh` to generate necessary SSL certificates and key and place in the folder `secrets/pki/`.
4. Follow manual setup instructions in `infra/manual_setup.md` to prepare a physical machines for ansible.
5. Navigate to the `terraform/` directory and follow the `README.md` in that directory for instructions.
6. After the resources are provisioned, update the Ansible inventory file with the newly created server details.
7. Navigate to the `ansible/` directory and run the appropriate playbooks to configure the servers.
    - You many need to run `ansible-galaxy collection install -r collections/requirements.yml`.
    - Run `ansible-playbook -i inventory.no-git.txt playbook.yml` to apply the configuration to all servers.

## Teardown

To tear down the infrastructure, navigate to the `terraform/` directory and run `terraform destroy`. This will remove all the resources that were created during the setup process.  Any physical machines or manually configured resources will need to be cleaned up separately.
