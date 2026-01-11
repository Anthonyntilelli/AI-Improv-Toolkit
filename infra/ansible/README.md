# Role Provisioning and Configuration with Ansible

This directory contains Ansible playbooks and roles for provisioning and configuring servers used in the AI Improv Toolkit project. The playbooks automate the setup of software, services, and configurations on the servers to ensure consistency and reliability across the infrastructure.

## Roles

- `base`: Base set up for all servers.
- `physical`: Configuration for physical servers.
- `nats`: Set up NATS messaging system.

__Note__: More roles to be added over time.

## Pre-requisites

- Create the Ansible inventory file `inventory` (use `inventory.no-git.txt` to be gitignored) based on your infrastructure setup and assign appropriate groups to the servers.
- Ensure you have SSH access to the servers with the necessary permissions to perform configuration tasks.
- Follow main infra/README.md to set up necessary environmental variables and PKI.

## Running Playbooks

1. Set up the needed groupVar files in `group_vars/` as needed for your environment. See `group_vars/all/var.examples` for reference.
2. Install required Ansible collections:

    ```bash
   ansible-galaxy collection install -r collections/requirements.yml
   ```

3. Run the playbook to configure the servers:

   ```bash
   ansible-playbook -i inventory.no-git.txt playbook.yml
   ```
