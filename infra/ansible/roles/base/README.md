Base Role
=========

An Ansible role to set up the base configuration for the AI Improv Toolkit systems.

Requirements
------------

- Debian based system (Debian 13 preferred)

Role Variables
--------------

- `base_sysadmin_ssh_pubkey`: The SSH public key for the `sysadmin` user to be added to their `authorized_keys` file.

- `base_show_sub_dirs`: A list of subdirectories to create under `/opt/show`. Default includes `setting`, `nats`, `ingest`, `vision`, `hearing`, `brain`, and `output`.
  - Do not include `pki` as it has special permissions.

Dependencies
------------

- None

Example Playbook
----------------

- hosts: servers
  roles:
  - { role: base, base_sysadmin_ssh_pubkey: "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC..." }

License
-------

This role is licensed under the LGPL-3.0-only license. See the LICENSE file for details.

Author Information
------------------

- Anthony Tilelli
