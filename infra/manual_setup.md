# Manual Setup Instructions

Some components of the AI Improv Toolkit infrastructure will require manual setup before the fully automated provisioning
can take place. This document outlines the necessary steps to prepare any physical machines or manually configured resources.
These steps should be completed before running the Terraform and Ansible automation. This will be for the ingestion/output
machine that will be at the physical location of the improv performance.

## Tested hardware and OS

The following hardware and operating systems have been tested and are known to work with the AI Improv Toolkit infrastructure:

- Hardware: Intel NUC with at least 16GB RAM and 1 TB SSD
- Operating System: Debian 13 x86_64

## Manual Setup Steps

1) Install the Operating System:

    - Download the Debian 13 ISO from the official website.
    - Create a bootable USB drive using tools like Rufus or Etcher.
    - Boot the target machine from the USB drive and follow the installation prompts to install Debian 13.

2) Set up the user `sysadmin` as the primary user on the machine with sudo privileges.
3) Set up the machine to use `tasksel` ssh server and base utilities.
4) Make note of the wifi interface name (e.g: wlo1).  It can be different on each box.
5) Remove bootable USB and restart machine.
6) From ansible control machine run the command `ssh-copy-id -i ~/.ssh/show_key.pub sysadmin@<hostname or ip>`
    - Adjust the command for your machine.
7) Add this machine to the inventory.
