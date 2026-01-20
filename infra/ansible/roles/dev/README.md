Dev Role
=========

Adds a developer user with sudo privileges and SSH access.

Requirements
------------

Based on Debian/Ubuntu systems.

Role Variables
--------------

Create a user named `developer` that is intended to be used by vscode remote development extensions
and other dev-related tasks.

Dependencies
------------

- base

Example Playbook
----------------

``` yaml
    - hosts: servers
      roles:
          { role: dev}
```

License
-------

This role is licensed under the LGPL-3.0-only license. See the LICENSE file for details.

Author Information
------------------

- Anthony Tilelli
