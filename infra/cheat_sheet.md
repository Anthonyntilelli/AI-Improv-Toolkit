# Cheat Sheet

This document provides a small set of command that may be useful during the show.

## Setting up the Wifi

```bash
nmcli radio wifi on
nmcli device status
nmcli device wifi list
nmcli device wifi connect "SSID" password "PASSWORD"
nmcli connection modify "SSID" connection.autoconnect yes
```

## Getting ssh key to known_hosts file

```bash
ssh-keyscan node.example.me >> ~/.ssh/known_hosts
```
