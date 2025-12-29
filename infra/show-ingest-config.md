# Show-ingest pc base config  (debian 13 server base)

## Prerequisite

### Base install

- user: `sysadmin` created
- Debian 13
- tasksel (laptop and ssh-server)

### Note from host pc

`ssh-copy-id -i ~/.ssh/id_ed25519.pub sysadmin@show-ingest`

## Post Install (all steps as root)

### Base Update (MIN)

```bash
apt update && apt full-upgrade -y

apt install -y timeshift jq rsync

timedatectl set-timezone America/New_York

reboot
```

### timeshift

```bash
# RSYNC Exclude in file "/etc/timeshift/timeshift.json"
: <<'COMMENT'
"exclude": [
  "/home/**",
  "/root/.cache/**",
  "/var/cache/**",
  "/var/tmp/**",
  "/var/log/journal/**",

  "/var/lib/containerd/**",
  "/opt/containerd/**",
  "/opt/nri/**",

  "/var/lib/docker/**",
  "/var/lib/containers/**",

  "/mnt/**",
  "/media/**",

  "/opt/show/**",
  "/tmp/**"
]
COMMENT

timeshift --rsync
jq --color-output . /etc/timeshift/timeshift.json

cat >/etc/apt/apt.conf.d/50timeshift <<'EOF'
DPkg::Pre-Invoke {
  "timeshift --create --comments 'Before APT transaction' --tags D";
};
EOF
```

###  Extra Packages

```bash
apt install -y evtest vim alsa-utils \
openssl pciutils usbutils \
htop netcat-openbsd dnsutils \
tr head awk grep \
sed
```

### Backports: Kernel + Firmware

```bash
touch /etc/apt/sources.list.d/debian-backports.sources
chmod 644 /etc/apt/sources.list.d/debian-backports.sources
chown root:root /etc/apt/sources.list.d/debian-backports.sources

cat <<'EOF' |  tee /etc/apt/sources.list.d/debian-backports.sources > /dev/null
Types: deb deb-src
URIs: http://deb.debian.org/debian
Suites: trixie-backports
Components: main
Enabled: yes
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
EOF

cat >/etc/apt/preferences.d/99-backports-kernel <<EOF
Package: linux-image-amd64 linux-headers-amd64
Pin: release a=trixie-backports
Pin-Priority: 990
EOF

apt update

apt -t trixie-backports install -y \
  linux-image-amd64 \
  firmware-linux \
  firmware-linux-nonfree \
  firmware-iwlwifi \
  firmware-realtek

reboot
```

### Service user and directory

```bash
mkdir -p -m 0750 /opt/show

getent group show >/dev/null || addgroup --system --gid 495 show
getent group  >/dev/null || addgroup ssh-users

id -u show >/dev/null 2>&1 || adduser --system \
  --home /opt/show \
  --no-create-home \
  --shell /usr/sbin/nologin \
  --uid 495 --gid 495 \
  --comment "Show runner account" \
  show

id -u dev >/dev/null 2>&1 || adduser dev
usermod -aG show dev
usermod -aG sudo dev
usermod -aG ssh-users dev
usermod -aG ssh-users sysadmin
```

### Connect wifi

```bash
nmcli radio wifi on
nmcli device status
nmcli device wifi list
nmcli device wifi connect "SSID" password "PASSWORD"
nmcli connection modify "SSID" connection.autoconnect yes
```

### install docker

```bash
apt install -y ca-certificates curl
# Add Docker's official GPG key:
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: $(. /etc/os-release && echo "$VERSION_CODENAME")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker

usermod -aG docker dev
su - dev -c "docker run --rm hello-world"
```

## dev user ssh access

```bash
sudo mkdir -p --mode 755 /etc/ssh/authorized_keys
install -m 0600 -o dev -g dev /home/sysadmin/.ssh/authorized_keys /etc/ssh/dev
install -m 0600 -o sysadmin -g sysadmin /home/sysadmin/.ssh/authorized_keys /etc/ssh/sysadmin
rm /home/sysadmin/.ssh/authorized_keys
```

### SSH Hardening

```bash
# SSH is now on port 8022
cat >/etc/ssh/sshd_config.d/10-show-ingest.conf <<'EOF'
Port 8022
AuthenticationMethods publickey
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
AllowGroups ssh-users
MaxAuthTries 3
X11Forwarding no
UsePAM yes
# Put authorized_keys outside encrypted homes (fscrypt-friendly)
AuthorizedKeysFile /etc/ssh/authorized_keys/%u
EOF

sshd -t && systemctl reload ssh
```

### Firewall and sshguard

```bash
apt install -y firewalld sshguard

firewall-cmd --set-default-zone=public
firewall-cmd --permanent --add-port=8022/tcp
firewall-cmd --permanent --zone=trusted --add-interface=docker0
firewall-cmd --reload

cat >/etc/default/sshguard <<EOF
BACKEND="firewalld"
EOF
systemctl restart  sshguard

systemctl enable --now firewalld
systemctl enable --now sshguard

systemctl status firewalld --no-pager
systemctl status sshguard --no-pager
```

### Show folder

```bash
mkdir -p /opt/show/{setting,nats,pki,ingest,vision,hearing,brain,output}

chown root:show /opt/show
chmod 0750 /opt/show

chown root:root /opt/show/pki
chmod 0700 /opt/show/pki

chown show:show /opt/show/{setting,nats,ingest,vision,hearing,brain,output}
chmod 0750 /opt/show/{setting,nats,ingest,vision,hearing,brain,output}
```

### Bluetooth

```bash
apt install -y bluez
systemctl enable --now bluetooth

bluetoothctl <<'EOF'
power on
agent on
default-agent
scan on
EOF

# TODO: FIND MAC address
bluetoothctl
# in the interactive shell:
pair AA:BB:CC:DD:EE:FF
trust AA:BB:CC:DD:EE:FF
connect AA:BB:CC:DD:EE:FF
quit


bluetoothctl <<EOF
pairable on
scan off
discoverable off
EOF

```

### HID

#### TODO REAL VIP/UID

``` bash
cat <<'EOF' > /etc/tmpfiles.d/dev-show.conf
d /dev/show 0755 root root -
EOF

systemd-tmpfiles --create


cat >/etc/udev/rules.d/70-show-hid.rules <<EOF
# USB actors (same VID/PID, distinguished by physical port)
SUBSYSTEM=="hidraw", KERNEL=="hidraw*", ATTRS{idVendor}=="XXXX", ATTRS{idProduct}=="YYYY", KERNELS=="1-3", GROUP="show", MODE="0660", SYMLINK+="show/actor1"
SUBSYSTEM=="hidraw", KERNEL=="hidraw*", ATTRS{idVendor}=="XXXX", ATTRS{idProduct}=="YYYY", KERNELS=="1-4", GROUP="show", MODE="0660", SYMLINK+="show/actor2"
# Bluetooth device distinguished by uniq (MAC)
SUBSYSTEM=="hidraw", KERNEL=="hidraw*", ENV{ID_BUS}=="bluetooth", ATTRS{uniq}=="AA:BB:CC:DD:EE:FF", GROUP="show", MODE="0660", SYMLINK+="show/bt-panic"
# Fallback USB panic (VID/PID only) – consider adding a port match too if multiple exist
SUBSYSTEM=="hidraw", KERNEL=="hidraw*", ATTRS{idVendor}=="XXXX", ATTRS{idProduct}=="YYYY", GROUP="show", MODE="0660", SYMLINK+="show/usb-panic"
EOF

cat > /etc/udev/rules.d/75-show-input-ignore.rules <<'EOF'
# For the keyboard-emulating HID(s): prevent desktop uaccess ACLs, restrict permissions,
# and also tell libinput to ignore (Wayland/X won't treat it as a keyboard).
SUBSYSTEM=="input", KERNEL=="event*", ATTRS{idVendor}=="XXXX", ATTRS{idProduct}=="YYYY", GROUP="show", MODE="0660", TAG-="uaccess", TAG-="seat", ENV{LIBINPUT_IGNORE_DEVICE}="1"
#TODO OTHER 3 inputs
EOF

udevadm control --reload-rules
udevadm trigger

ls -l /dev/show/
```

### Encrypt /home directory of sysadmin and dev

```bash
apt install -y fscrypt libpam-fscrypt
fscrypt status / # NOTE: MUST be yes
fscrypt setup /
```

#### Log in as dev (become root)

```bash
loginctl terminate-user sysadmin
fscrypt encrypt /home/sysadmin --user=sysadmin
# You will be prompted to set a recovery passphrase → store it offline (password manager / vault).
```

#### Log in as sysadmin (become root)

```bash
loginctl terminate-user dev
fscrypt encrypt /home/dev --user=dev
# You will be prompted to set a recovery passphrase → store it offline (password manager / vault).
```

#### Verify

```bash
fscrypt status /home/sysadmin
fscrypt status /home/dev
````

### Timeshift final

```bash
# Delete all intermediate snapshots (not preConfig)
timeshift --delete-all
systemctl stop docker
timeshift --create --comments "baseConfig" --yes --scripted
systemctl start docker
```
