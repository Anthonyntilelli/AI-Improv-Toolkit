Physical Role
=========

An Ansible role that sets up configurations specific to physical machines.

Requirements
------------

- Debian based system (Debian 13 preferred) with only ssh-server and base utils tasksel installed.

Role Variables
--------------

- `physical_wifi_ssid` : SSID of the WiFi network to connect to.
- `physical_wifi_password`: Password for the WiFi network.
- `physical_wifi_iface`:  Network interface to use for WiFi connection. Default is `wlan0`.
- `physical_wifi_autoconnect`: Boolean to determine if the WiFi connection should autoconnect on boot. Default is `true`.

Dependencies
------------

- base

Example Playbook
----------------

- hosts: servers
  roles:
      - { role: physical, physical_wifi_ssid: "Your_SSID", physical_wifi_password: "Your_Password" } <!-- pragma: allowlist secret ---> <!-- markdownlint-disable-line -->

License
-------

This role is licensed under the LGPL-3.0-only license. See the LICENSE file for details.

Author Information
------------------

- Anthony Tilelli
