NATS Role
=========

An Ansible role that sets up and deploys a NATS server.

Requirements
------------

- A Debian based system.
- Docker installed on the target system.
- Base Roles installed on the target system.

Role Variables
--------------

- `nats_debug_mode` : Enable or disable debug mode. Default is `false`.
- `nats_docker_tag` : Docker image tag for the NATS server. Default is `2.12.3`.
- `nats_pki_cert_path` : Path to the NATS server certificate on host.
- `nats_pki_key_path` : Path to the NATS server key on host.
- `nats_pki_ca_path` : Path to the NATS CA certificate on host.

Dependencies
------------

- base

Example Playbook
----------------

```yaml
- hosts: servers
  roles:
    - role: nats
      nats_debug_mode: "{{ nats_debug_mode }}"
      nats_docker_tag: "{{ nats_docker_tag }}"
      nats_pki_cert_path: "{{ nats_pki_cert_path }}"
      nats_pki_key_path: "{{ nats_pki_key_path }}"
      nats_pki_ca_path: "{{ nats_pki_ca_path }}"
```

License
-------

This role is licensed under the LGPL-3.0-only license. See the LICENSE file for details.

Author Information
------------------

- Anthony Tilelli
