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
      nats_docker_tag: "2.12.3"
      nats_pki_cert_path: "/path/to/cert.pem"
      nats_pki_key_path: "/path/to/key.pem"
      nats_pki_ca_path: "/path/to/ca.pem"
```

License
-------

This role is licensed under the LGPL-3.0-only license. See the LICENSE file for details.

Author Information
------------------

- Anthony Tilelli
