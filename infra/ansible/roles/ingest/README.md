Ingest Role
=========

An Ansible role to set up the Ingest component for the AI Improv Toolkit.

Requirements
------------

- A Debian based system.
- Docker installed on the target system.
- Base and physical Roles installed on the target system.

Role Variables
--------------

"`ingest_docker_tag` : Docker image tag for the Ingest service. Default is `latest`.
"`ingest_pki_cert_path` : Path to the Ingest service certificate on host.
"`ingest_pki_key_path` : Path to the Ingest service key on host.
"`ingest_pki_ca_path` : Path to the Ingest service CA certificate on host.

Dependencies
------------

- base
- physical

Example Playbook
----------------

```yaml
- hosts: servers
  roles:
    - role: ingest
      ingest_docker_tag: "latest"
      ingest_pki_cert_path: "/path/to/cert.pem"
      ingest_pki_cert_path: "/path/to/key.pem"
      ingest_pki_ca_path: "/path/to/ca.pem"
```

License
-------

This role is licensed under the LGPL-3.0-only license. See the LICENSE file for details.

Author Information
------------------

- Anthony Tilelli
