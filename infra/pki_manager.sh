#!/usr/bin/env bash
################ Script metadata ###############################################
#: Title        : PKI Manager
#: Author       : Anthony Tilelli
#: Description  : Basic PKI management for the project using openssl, it can:
#:              : - Generate root, intermediate, Server and Client CA
#:              : - Generate new client and Server CA, while revoking old ones
#:              : - Verify chain, CRLs, and all leaf certs\n"
#: WARNING      :
#:              : This script makes use of env variable but a script cannot clear them.
#:              : Be sure to clear env variables when done.
#: Requirements :
#:              : BASH 5.0+
#:              : openssl
#:              : tar
#:              : mktemp
#:              : tr
#:              : head
#:              : find
#:              : grep
#:              : awk
#:              : sed
#: Options      :
#:              : init   - Generate root, intermediate, Server and Client CA
#:              : rotate - Generate new client and Server CA, while revoking old ones
#:              : verify -  Verify chain, CRLs, and all leaf certs\n"
#: ENV Variables:
#:              : ROOT_CA_PASSWORD <- Password For Root CA
#:              : INTERMEDIATE_CA_PASSWORD <- Password For intermediate CA
#: Version      :
#:              : 0.0.1 (https://semver.org/)
#: ExitCodes    :
#:              : (reserved https://www.tldp.org/LDP/abs/html/exitcodes.html)
#:              : 0 "Success"
#:              : 1 General Failure (varied message)
#:              : 3 Bash-5.0+ is required to run this script
#:              : 4 <command> is missing, Install it please, and then run this tool again.
#:              : 5 <ENV Variable> is missing, please set it then run this tool again.
#:              : 6 Could not cd to directory <DIRECTORY>.
#:              : 7 Command Line argument missing.
#:              : 8 <option> is not a valid option (init | rotate).
#:              : 9 Invalid mode in main: <mode>.
#:              : 10 Invalid Folder or missing PKI items  (varied message).
#:              : 11 Invalid INTERMEDIATE_CA_PASSWORD or missing INTERMEDIATE Key  (varied message).
#:              : 12 Verify failed (varied message)
################ Script metadata ###############################################

# strict mode
# http://redsymbol.net/articles/unofficial-bash-strict-mode/
# https://disconnected.systems/blog/another-bash-strict-mode/
set -euo pipefail
IFS=$'\n\t'
umask 077

# Version Check
if ((BASH_VERSINFO < 5))
then
  printf "Bash-5.0+ is required to run this script \\n" >&2
  exit 3
fi


# Modify the below constants to match your domain and information
readonly COUNTRY="US"
readonly STATE="Pennsylvania"
readonly LOCAL="Mechanicsburg"
readonly ORG="Anthony"
readonly ORGUNIT="Improv Show"
readonly SERVER_DOMAIN="tilelli.me"

# Constants
declare -rA CLIENTS=(
  [setting]="setting@improvShow.local"
  [debug]="debug@improvShow.local"
  [ingest]="ingest@improvShow.local"
  [vision]="vision@improvShow.local"
  [hearing]="hearing@improvShow.local"
  [brain]="brain@improvShow.local"
  [output]="output@improvShow.local"
)
readonly -a SERVERS=(nats vision hearing)

# Global
declare mode="unset"
declare ARCHIVE_DIR="unset"

# Functions
function die() {
  #@ DESCRIPTION: prints error-message and exits script
  #@ USAGE: die ERRORCODE ERROR_MESSAGE or die
  #@ REQUIREMENTS: NONE

  local -r ERRORCODE="${1:-1}"
  local -r ERROR_MESSAGE="${2:-"No \"ERROR_MESSAGE\" provided"}"
  local -r TIMESTAMP="$(date)"
  printf "FATAL %d: %s: %s\\n" "$ERRORCODE" "$TIMESTAMP" "$ERROR_MESSAGE" >&2
  exit "$ERRORCODE"
}

function output() {
  #@ DESCRIPTION:  prints message
  #@ USAGE:  output <MESSAGE>
  #@ REQUIREMENTS: NONE

  local -r MESSAGE="${1:-"No \"MESSAGE\" provided"}"
  local -r TIMESTAMP="$(date)"
  printf "%s: (%s)\\n" "$MESSAGE" "$TIMESTAMP"
  return 0
}

function usage() {
  #@ DESCRIPTION: Print usage information
  #@ USAGE:  usage
  #@ REQUIREMENTS: NONE

  printf "pki_management (init | rotate)\\n"
  printf "    init        Generate root, intermediate, Server and Client CA\\n"
  printf "    rotate      Generate new client and Server CA, while revoking old ones\\n"
  printf "    verify      Verify chain, CRLs, and all leaf certs\n"
  return 0
}


function cli_check() {
  #@ DESCRIPTION:  Check if needed CLI commands are in place.
  #@ USAGE:  cli_check
  #@ REQUIREMENTS: NONE

  command -v openssl &>/dev/null || die 4 "openssl is missing, Install it please, and then run this tool again."
  command -v mktemp  &>/dev/null || die 4 "mktemp is missing, Install it please, and then run this tool again."
  command -v tar     &>/dev/null || die 4 "tar is missing, Install it please, and then run this tool again."
  command -v tr      &>/dev/null || die 4 "tr is missing, Install it please, and then run this tool again."
  command -v head    &>/dev/null || die 4 "head is missing, Install it please, and then run this tool again."
  command -v find    &>/dev/null || die 4 "find is missing, Install it please, and then run this tool again."
  command -v grep    &>/dev/null || die 4 "grep is missing, Install it please, and then run this tool again."
  command -v awk     &>/dev/null || die 4 "awk is missing, Install it please, and then run this tool again."
  command -v sed     &>/dev/null || die 4 "sed is missing, Install it please, and then run this tool again."
  return 0
}

function env_check() {
  #@ DESCRIPTION:  Check if needed ENV Variable are in place.
  #@ USAGE:  env_check
  #@ REQUIREMENTS: NONE

  if [[ "$mode" == "init" ]]; then
    if ! [[ -v ROOT_CA_PASSWORD ]]; then
      die 5 "ROOT_CA_PASSWORD is missing, please set it then run this tool again."
    fi
  fi
  if ! [[ -v INTERMEDIATE_CA_PASSWORD ]]; then
    die 5 "INTERMEDIATE_CA_PASSWORD is missing, please set it then run this tool again."
  fi

  return 0
}

function gen_folders() {
  #@ DESCRIPTION:  generated folder structure for PKI solution in CWD
  #@ USAGE: gen_folders
  #@ REQUIREMENTS:

  mkdir -p rootCA/{certs,crl,newcerts,private,csr}
  mkdir -p intermediateCA/{certs,crl,newcerts,private,csr}
  chmod 700 {rootCA,intermediateCA}/private
  echo 1000 > rootCA/serial
  echo 1000 > intermediateCA/serial
  echo 0100 > rootCA/crlnumber
  echo 0100 > intermediateCA/crlnumber
  : > rootCA/private/.rand
  : > intermediateCA/private/.rand
  chmod 600 rootCA/private/.rand intermediateCA/private/.rand
  touch rootCA/index.txt
  touch intermediateCA/index.txt
  return 0
}


function gen_root_config() {
  #@ DESCRIPTION:  generated ROOT config in CWD (FILE: openssl_root.cnf).
  #@ USAGE: gen_root_config
  #@ REQUIREMENTS: NONE

  cat <<'EOF' > openssl_root.cnf
[ ca ]                                                   # The default CA section
default_ca = CA_default                                  # The default CA name

[ CA_default ]                                           # Default settings for the CA
dir               = ./rootCA                             # CA directory
certs             = $dir/certs                           # Certificates directory
crl_dir           = $dir/crl                             # CRL directory
new_certs_dir     = $dir/newcerts                        # New certificates directory
database          = $dir/index.txt                       # Certificate index file
serial            = $dir/serial                          # Serial number file
RANDFILE          = $dir/private/.rand                   # Random number file
private_key       = $dir/private/ca.key.pem              # Root CA private key
certificate       = $dir/certs/ca.cert.pem               # Root CA certificate
crl               = $dir/crl/ca.crl.pem                  # Root CA CRL
crlnumber         = $dir/crlnumber                       # Root CA CRL number
crl_extensions    = crl_ext                              # CRL extensions
default_crl_days  = 30                                   # Default CRL validity days
default_md        = sha256                               # Default message digest
preserve          = no                                   # Preserve existing extensions
email_in_dn       = no                                   # Exclude email from the DN
name_opt          = ca_default                           # Formatting options for names
cert_opt          = ca_default                           # Certificate output options
policy            = policy_strict                        # Certificate policy
unique_subject    = no                                   # Allow multiple certs with the same DN

[ policy_strict ]                                        # Policy for stricter validation
countryName             = match                          # Must match the issuer's country
stateOrProvinceName     = match                          # Must match the issuer's state
organizationName        = match                          # Must match the issuer's organization
organizationalUnitName  = optional                       # Organizational unit is optional
commonName              = supplied                       # Must provide a common name
emailAddress            = optional                       # Email address is optional

[ req ]                                                  # Request settings
default_bits        = 4096                               # Default key size
distinguished_name  = req_distinguished_name             # Default DN template
string_mask         = utf8only                           # UTF-8 encoding
default_md          = sha256                             # Default message digest
prompt              = no                                 # Non-interactive mode

[ req_distinguished_name ]                               # Template for the DN in the CSR
countryName                     = Country Name (2 letter code)
stateOrProvinceName             = State or Province Name (full name)
localityName                    = Locality Name (city)
0.organizationName              = Organization Name (company)
organizationalUnitName          = Organizational Unit Name (section)
commonName                      = Common Name (your domain)
emailAddress                    = Email Address

[ v3_ca ]                                           # Root CA certificate extensions
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints = critical, CA:true
keyUsage = critical, keyCertSign, cRLSign

[ crl_ext ]
authorityKeyIdentifier = keyid:always,issuer

[ v3_intermediate_ca ]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints = critical, CA:true, pathlen:0
keyUsage = critical, digitalSignature, cRLSign, keyCertSign
EOF

chmod 400 openssl_root.cnf
return 0
}

function gen_intermediary_config() {
  #@ DESCRIPTION:  generated intermediate config in CWD (FILE: openssl_intermediate.cnf).
  #@ USAGE: gen_intermediary_config
  #@ REQUIREMENTS: NONE

 cat <<'EOF' > openssl_intermediate.cnf
[ ca ]                           # The default CA section
default_ca = CA_default          # The default CA name

[ CA_default ]                                           # Default settings for the intermediate CA
dir               = ./intermediateCA                     # Intermediate CA directory
certs             = $dir/certs                           # Certificates directory
crl_dir           = $dir/crl                             # CRL directory
new_certs_dir     = $dir/newcerts                        # New certificates directory
database          = $dir/index.txt                       # Certificate index file
serial            = $dir/serial                          # Serial number file
RANDFILE          = $dir/private/.rand                   # Random number file
private_key       = $dir/private/intermediate.key.pem    # Intermediate CA private key
certificate       = $dir/certs/intermediate.cert.pem     # Intermediate CA certificate
crl               = $dir/crl/intermediate.crl.pem        # Intermediate CA CRL
crlnumber         = $dir/crlnumber                       # Intermediate CA CRL number
crl_extensions    = crl_ext                              # CRL extensions
default_crl_days  = 30                                   # Default CRL validity days
default_md        = sha256                               # Default message digest
preserve          = no                                   # Preserve existing extensions
email_in_dn       = no                                   # Exclude email from the DN
name_opt          = ca_default                           # Formatting options for names
cert_opt          = ca_default                           # Certificate output options
policy            = policy_loose                         # Certificate policy

[ policy_loose ]                                         # Policy for less strict validation
countryName             = optional                       # Country is optional
stateOrProvinceName     = optional                       # State or province is optional
localityName            = optional                       # Locality is optional
organizationName        = optional                       # Organization is optional
organizationalUnitName  = optional                       # Organizational unit is optional
commonName              = supplied                       # Must provide a common name
emailAddress            = optional                       # Email address is optional

[ req ]                                                  # Request settings
default_bits        = 4096                               # Default key size
distinguished_name  = req_distinguished_name             # Default DN template
string_mask         = utf8only                           # UTF-8 encoding
default_md          = sha256                             # Default message digest
x509_extensions     = v3_intermediate_ca                 # Extensions for intermediate CA certificate

[ req_distinguished_name ]                               # Template for the DN in the CSR
countryName                     = Country Name (2 letter code)
stateOrProvinceName             = State or Province Name
localityName                    = Locality Name
0.organizationName              = Organization Name
organizationalUnitName          = Organizational Unit Name
commonName                      = Common Name
emailAddress                    = Email Address

[ v3_intermediate_ca ]                                      # Intermediate CA certificate extensions
subjectKeyIdentifier = hash                                 # Subject key identifier
authorityKeyIdentifier = keyid:always,issuer                # Authority key identifier
basicConstraints = critical, CA:true, pathlen:0             # Basic constraints for a CA
keyUsage = critical, digitalSignature, cRLSign, keyCertSign # Key usage for a CA

[ crl_ext ]                                                 # CRL extensions
authorityKeyIdentifier=keyid:always                         # Authority key identifier

[ server_cert ]                                             # Server certificate extensions
basicConstraints = CA:FALSE                                 # Not a CA certificate
keyUsage = critical, digitalSignature, keyEncipherment      # Key usage for a server cert
extendedKeyUsage = serverAuth                               # Extended key usage for server authentication purposes (e.g., TLS/SSL servers).
authorityKeyIdentifier = keyid,issuer                       # Authority key identifier linking the certificate to the issuer's public key.
subjectKeyIdentifier = hash
EOF

  chmod 400 openssl_intermediate.cnf
  return 0
}

function gen_client_config(){
  #@ DESCRIPTION:  generated intermediate config in CWD (FILE: client_cert_ext.cnf).
  #@ USAGE: gen_intermediary_config
  #@ REQUIREMENTS: NONE

  for key in "${!CLIENTS[@]}"; do
    cat << 'EOF' > "client_cert_ext_${key}.cnf"
[ ca ]                           # The default CA section
default_ca = CA_default          # The default CA name

[ CA_default ]                                           # Default settings for the intermediate CA
dir               = ./intermediateCA                     # Intermediate CA directory
certs             = $dir/certs                           # Certificates directory
crl_dir           = $dir/crl                             # CRL directory
new_certs_dir     = $dir/newcerts                        # New certificates directory
database          = $dir/index.txt                       # Certificate index file
serial            = $dir/serial                          # Serial number file
RANDFILE          = $dir/private/.rand                   # Random number file
private_key       = $dir/private/intermediate.key.pem    # Intermediate CA private key
certificate       = $dir/certs/intermediate.cert.pem     # Intermediate CA certificate
crl               = $dir/crl/intermediate.crl.pem        # Intermediate CA CRL
crlnumber         = $dir/crlnumber                       # Intermediate CA CRL number
crl_extensions    = crl_ext                              # CRL extensions
default_crl_days  = 30                                   # Default CRL validity days
default_md        = sha256                               # Default message digest
preserve          = no                                   # Preserve existing extensions
email_in_dn       = no                                   # Exclude email from the DN
name_opt          = ca_default                           # Formatting options for names
cert_opt          = ca_default                           # Certificate output options
policy            = policy_loose                         # Certificate policy

[ policy_loose ]                                         # Policy for less strict validation
countryName             = optional                       # Country is optional
stateOrProvinceName     = optional                       # State or province is optional
localityName            = optional                       # Locality is optional
organizationName        = optional                       # Organization is optional
organizationalUnitName  = optional                       # Organizational unit is optional
commonName              = supplied                       # Must provide a common name
emailAddress            = optional                       # Email address is optional

[ req ]                                                  # Request settings
default_bits        = 4096                               # Default key size
distinguished_name  = req_distinguished_name             # Default DN template
string_mask         = utf8only                           # UTF-8 encoding
default_md          = sha256                             # Default message digest

[ req_distinguished_name ]                               # Template for the DN in the CSR
countryName                     = Country Name (2 letter code)
stateOrProvinceName             = State or Province Name
localityName                    = Locality Name
0.organizationName              = Organization Name
organizationalUnitName          = Organizational Unit Name
commonName                      = Common Name
emailAddress                    = Email Address

[ client_cert ]
basicConstraints = CA:FALSE
nsComment = "Client Certificate used for Improv Show"
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth
subjectAltName = @alt_names
EOF
cat << EOF >> "client_cert_ext_${key}.cnf"
[ alt_names ]
email = ${CLIENTS[$key]}
EOF
  done
  return 0
}


function gen_root_ca() {
  #@ DESCRIPTION:  generated ROOT config and certifications in cwd assuming standard structure.
  #@ Config FILE: openssl_root.cnf
  #@ Cert FILE: rootCA/certs/ca.cert.pem
  #@ Key FILE: rootCA/private/ca.key.pem
  #@ USAGE: gen_root_config
  #@ REQUIREMENTS: openssl gen_root_config()

  gen_root_config
  openssl genrsa -out rootCA/private/ca.key.pem -aes256 -passout env:ROOT_CA_PASSWORD 4096
  chmod 400 rootCA/private/ca.key.pem

  openssl req \
  -config openssl_root.cnf \
  -key rootCA/private/ca.key.pem \
  -passin env:ROOT_CA_PASSWORD \
  -new -x509 \
  -days 7300 \
  -sha256 \
  -extensions v3_ca \
  -out rootCA/certs/ca.cert.pem \
  -subj "/C=${COUNTRY}/ST=${STATE}/L=${LOCAL}/O=${ORG}/OU=${ORGUNIT}/CN=Root CA"

  chmod 444 rootCA/certs/ca.cert.pem
  return 0
}

function gen_intermediary_ca() {
  #@ DESCRIPTION: generated ROOT config and certifications in cwd assuming standard structure.
  #@ requires existence of ROOT CA/KEY and root password
  #@ Config FILE: openssl_root.cnf
  #@ Cert FILE: rootCA/certs/intermediate.cert.pem
  #@ Key FILE: rootCA/private/intermediate.key.pem
  #@ USAGE: gen_intermediary_config
  #@ REQUIREMENTS: openssl gen_intermediary_config()

  gen_intermediary_config
  openssl genrsa -out intermediateCA/private/intermediate.key.pem -aes256 -passout env:INTERMEDIATE_CA_PASSWORD 4096
  chmod 400 intermediateCA/private/intermediate.key.pem

  openssl req \
  -config openssl_intermediate.cnf \
  -key intermediateCA/private/intermediate.key.pem \
  -new -sha256 \
  -out intermediateCA/csr/intermediate.csr.pem \
  -passin env:INTERMEDIATE_CA_PASSWORD \
  -subj "/C=${COUNTRY}/ST=${STATE}/L=${LOCAL}/O=${ORG}/OU=${ORGUNIT}/CN=Intermediate CA"

  openssl ca \
  -config openssl_root.cnf \
  -extensions v3_intermediate_ca \
  -days 3650 -notext -md sha256 -quiet\
  -in intermediateCA/csr/intermediate.csr.pem \
  -passin env:ROOT_CA_PASSWORD -batch \
  -out intermediateCA/certs/intermediate.cert.pem >/dev/null 2>&1

  chmod 444 intermediateCA/certs/intermediate.cert.pem

  # Create Cert bundle and verify
  cat intermediateCA/certs/intermediate.cert.pem rootCA/certs/ca.cert.pem > intermediateCA/certs/ca-chain.cert.pem
  openssl verify -CAfile intermediateCA/certs/ca-chain.cert.pem \
  intermediateCA/certs/intermediate.cert.pem \
  >/dev/null 2>&1
  return 0
}

function gen_server_ca() {
  #@ DESCRIPTION: generated nats, hearing and vision server certifications in cwd assuming standard structure.
  #@ Warning: These certs are not password protected
  #@ USAGE: gen_server_ca
  #@ REQUIREMENTS: openssl

  for server in "${SERVERS[@]}" ; do
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -out "intermediateCA/private/${server}.${SERVER_DOMAIN}.key.pem"  2>/dev/null
    chmod 400 "intermediateCA/private/${server}.${SERVER_DOMAIN}.key.pem"

    openssl req -config openssl_intermediate.cnf \
      -key "intermediateCA/private/${server}.${SERVER_DOMAIN}.key.pem" \
      -new -sha256 -out "intermediateCA/csr/${server}.${SERVER_DOMAIN}.csr.pem" \
      -subj "/C=${COUNTRY}/ST=${STATE}/L=${LOCAL}/O=${ORG}/OU=${ORGUNIT}/CN=${server}.${SERVER_DOMAIN}"
    chmod 444 "intermediateCA/csr/${server}.${SERVER_DOMAIN}.csr.pem"

    openssl ca -config <(cat openssl_intermediate.cnf; cat <<EOF
[ server_cert ]
subjectAltName = @alt_names

[ alt_names ]
DNS.1 = ${server}.${SERVER_DOMAIN}
DNS.2 = ${SERVER_DOMAIN}
EOF
) \
      -extensions server_cert -days 375 -notext -md sha256  -batch \
      -in "intermediateCA/csr/${server}.${SERVER_DOMAIN}.csr.pem" \
      -passin env:INTERMEDIATE_CA_PASSWORD \
      -out "intermediateCA/certs/${server}.${SERVER_DOMAIN}.cert.pem" >/dev/null 2>&1

    chmod 444 "intermediateCA/certs/${server}.${SERVER_DOMAIN}.cert.pem"
    verify_leaf_cert "intermediateCA/certs/${server}.${SERVER_DOMAIN}.cert.pem" "sslserver"

    # SAN sanity check
    openssl x509 -in "intermediateCA/certs/${server}.${SERVER_DOMAIN}.cert.pem" -noout -text | \
      grep -q "DNS:${server}.${SERVER_DOMAIN}" \
      || die 1 "Missing expected SAN on ${server}.${SERVER_DOMAIN}"
  done
  return 0
}

function gen_client_ca() {
  #@ DESCRIPTION: generated setting, nats_debug, ingest, vision, hearing, brain, output
  #@ client certifications in cwd assuming standard structure.
  #@ Warning: These certs are not password protected
  #@ USAGE: gen_client_ca
  #@ REQUIREMENTS: openssl

  gen_client_config

  for key in "${!CLIENTS[@]}"; do
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -out "intermediateCA/private/${key}.client.key.pem"  2>/dev/null
    chmod 400 "intermediateCA/private/${key}.client.key.pem"

    openssl req -config "client_cert_ext_${key}.cnf"  \
    -key "intermediateCA/private/${key}.client.key.pem" \
    -new -sha256 -out "intermediateCA/csr/${key}.client.csr.pem" \
    -subj "/C=${COUNTRY}/ST=${STATE}/L=${LOCAL}/O=${ORG}/OU=${ORGUNIT}/CN=${key}.client"
    chmod 444 "intermediateCA/csr/${key}.client.csr.pem"

    openssl ca \
    -config "client_cert_ext_${key}.cnf" \
    -days 375 -notext -md sha256  -batch \
    -extensions client_cert \
    -in "intermediateCA/csr/${key}.client.csr.pem" \
    -passin env:INTERMEDIATE_CA_PASSWORD \
    -out "intermediateCA/certs/${key}.client.cert.pem" >/dev/null 2>&1
    chmod 444 "intermediateCA/certs/${key}.client.cert.pem"

    verify_leaf_cert "intermediateCA/certs/${key}.client.cert.pem" sslclient
    # Email SAN check
    openssl x509 -in "intermediateCA/certs/${key}.client.cert.pem" -noout -text | \
      grep -q "email:${CLIENTS[$key]}" \
      || die 1 "Missing expected email SAN on ${key}.client"
  done
  return 0
}

function gen_crls_root() {
  #@ DESCRIPTION: generated crl in CWD
  #@ USAGE: gen_crls_root
  #@ REQUIREMENTS: openssl

  openssl ca -config openssl_root.cnf -gencrl \
    -passin env:ROOT_CA_PASSWORD \
    -out rootCA/crl/ca.crl.pem >/dev/null 2>&1
  chmod 444 rootCA/crl/ca.crl.pem
  return 0
}

function gen_crls_intermediate() {
  #@ DESCRIPTION: generated crl in CWD
  #@ USAGE: gen_crls_intermediate
  #@ REQUIREMENTS: openssl

  openssl ca -config openssl_intermediate.cnf -gencrl \
    -passin env:INTERMEDIATE_CA_PASSWORD \
    -out intermediateCA/crl/intermediate.crl.pem >/dev/null 2>&1
  chmod 444 intermediateCA/crl/intermediate.crl.pem
  return 0
}

function require_existing_pki() {
  #@ DESCRIPTION: Ensure we are in an extracted PKI directory
  #@ USAGE: require_existing_pki
  #@ REQUIREMENTS: NONE

  # [[ -d rootCA ]] || die 10 "rootCA/ not found. Run rotate inside an extracted PKI directory."
  [[ -d intermediateCA ]] || die 10 "intermediateCA/ not found. Run rotate inside an extracted PKI directory."
  # [[ -f openssl_root.cnf ]] || die 10 "openssl_root.cnf not found."
  [[ -f openssl_intermediate.cnf ]] || die 10 "openssl_intermediate.cnf not found."
  [[ -f intermediateCA/private/intermediate.key.pem ]] || die 10 "Intermediate key missing at intermediateCA/private/intermediate.key.pem"
  [[ -f intermediateCA/certs/intermediate.cert.pem ]] || die 10 "Intermediate cert missing at intermediateCA/certs/intermediate.cert.pem"
  # [[ -f rootCA/certs/ca.cert.pem ]] || die 10 "Root cert missing at rootCA/certs/ca.cert.pem"
  return 0
}

function list_leaf_certs_to_rotate() {
  #@ DESCRIPTION: Print leaf cert paths to stdout (server + client), excluding CA/chain files
  # Server leaf certs:
  find intermediateCA/certs -maxdepth 1 -type f -name "*.${SERVER_DOMAIN}.cert.pem" -print 2>/dev/null || true
  # Client leaf certs:
  find intermediateCA/certs -maxdepth 1 -type f -name "*.client.cert.pem" -print 2>/dev/null || true
  return 0
}

function archive_leaf_material() {
  #@ DESCRIPTION: Move existing leaf keys/csrs/certs into an archive directory
  #@ USAGE: archive_leaf_material
  #@ REQUIREMENTS: NONE
  #@ OUTPUTS: sets global ARCHIVE_DIR
  local -r TS="$(date +%Y%m%d-%H%M%S)"
  ARCHIVE_DIR="intermediateCA/old/${TS}"
  mkdir -p "${ARCHIVE_DIR}"/{certs,csr,private}
  chmod 700 "${ARCHIVE_DIR}" "${ARCHIVE_DIR}/private"

  # Move leaf certs
  while IFS= read -r cert; do
    [[ -n "$cert" ]] || continue
    mv -f "$cert" "${ARCHIVE_DIR}/certs/" || die 1 "Failed to archive cert: ${cert}"
  done < <(list_leaf_certs_to_rotate)

  # Move matching CSRs and keys for known patterns
  for server in "${SERVERS[@]}"; do
    if [[ -f "intermediateCA/csr/${server}.${SERVER_DOMAIN}.csr.pem" ]]; then
      mv -f "intermediateCA/csr/${server}.${SERVER_DOMAIN}.csr.pem" "${ARCHIVE_DIR}/csr/"
    fi
    if [[ -f "intermediateCA/private/${server}.${SERVER_DOMAIN}.key.pem" ]]; then
      mv -f "intermediateCA/private/${server}.${SERVER_DOMAIN}.key.pem" "${ARCHIVE_DIR}/private/"
    fi
  done

  # Clients: keys/csrs by CLIENTS map keys
  for key in "${!CLIENTS[@]}"; do
    if [[ -f "intermediateCA/csr/${key}.client.csr.pem" ]]; then
      mv -f "intermediateCA/csr/${key}.client.csr.pem" "${ARCHIVE_DIR}/csr/"
    fi
    if [[ -f "intermediateCA/private/${key}.client.key.pem" ]]; then
      mv -f "intermediateCA/private/${key}.client.key.pem" "${ARCHIVE_DIR}/private/"
    fi
  done

  return 0
}

function revoke_archived_leaf_certs() {
  #@ DESCRIPTION: Revoke all archived leaf certs with reason superseded
  #@ USAGE: revoke_archived_leaf_certs
  #@ REQUIREMENTS: openssl

  local -r cert_dir="${ARCHIVE_DIR}/certs"
  [[ -d "$cert_dir" ]] || die 1 "Archive cert directory missing: ${cert_dir}"

  shopt -s nullglob
  local certs=( "${cert_dir}"/*.pem )
  shopt -u nullglob

  if (( ${#certs[@]} == 0 )); then
    output "No existing leaf certs found to revoke."
    return 0
  fi

  for cert in "${certs[@]}"; do
    # Skip any unexpected CA/chain files if they end up here
    case "$(basename "$cert")" in
      "intermediate.cert.pem"|"ca-chain.cert.pem") continue ;;
    esac

    # Revoke
    openssl ca \
      -config openssl_intermediate.cnf \
      -revoke "$cert" \
      -crl_reason superseded \
      -passin env:INTERMEDIATE_CA_PASSWORD \
      -batch >/dev/null 2>&1 || die 1 "Failed to revoke cert: ${cert}"
  done

  return 0
}

function verify_leaf_cert() {
  #@ DESCRIPTION: Verify the leaf certs
  #@ USAGE:  verify_leaf_cert <certPath> <purpose (sslserver | sslclient)>
  #@ REQUIREMENTS: openssl

  local -r CERT="$1"
  local -r PURPOSE="$2"
  local -r CHAIN="intermediateCA/certs/ca-chain.cert.pem"

  [[ -f "$CERT" ]] || die 1 "Missing cert: $CERT"
  [[ -f "$CHAIN" ]] || die 1 "Missing CA chain: $CHAIN"

  # Chain + purpose verification
  openssl verify \
    -CAfile "$CHAIN" \
    -purpose "$PURPOSE" \
    "$CERT" >/dev/null 2>&1 \
    || die 1 "Verification failed ($PURPOSE): $CERT"
}

function Verify_INTERMEDIATE_CA_PASSWORD() {
  #@ DESCRIPTION: Verifies INTERMEDIATE_CA_PASSWORD can decrypt the intermediate CA private key.
  #@ USAGE: Verify_INTERMEDIATE_CA_PASSWORD
  #@ REQUIREMENTS: openssl

  local -r KEY="intermediateCA/private/intermediate.key.pem"
  [[ -f "$KEY" ]] || die 11 "Intermediate key missing at ${KEY}"

  # Try to read key with provided password; fails fast if wrong.
  openssl pkey \
    -in "$KEY" \
    -passin env:INTERMEDIATE_CA_PASSWORD \
    -noout >/dev/null 2>&1 \
    || die 11 "INTERMEDIATE_CA_PASSWORD is invalid for ${KEY}"
}

function create_bundle(){
  #@ DESCRIPTION: Create PKI Encrypted tar.gz bundle and place in CWD
  #@ USAGE: create_bundle <PKI path>
  #@ REQUIREMENTS: openssl tar

  local -r CWD="$(pwd)"
  local -r PASSFILE="PKIBundle.pass"
  local -r BUNDLEPASSWORD="$(LC_ALL=C tr -dc 'A-Za-z0-9@%^&*()-_=+[]{}:,.?' </dev/urandom | head -c 24)"
  local -r PKIPATH="${1:?PKI path required}"

  [[ -d "$PKIPATH" ]] || die 1 "PKI path not a directory: $PKIPATH"
  [[ "${CWD}" == "${PKIPATH}" ]] &&  die 1 "CWD cannot be same as TarBall destination."
  ( umask 077 && printf "%s\n" "$BUNDLEPASSWORD" > "$PASSFILE" ) || die 1 "Failed to write bundle password file"
  tar -C "$PKIPATH" --owner=0 --group=0 --numeric-owner -czf - . | \
    openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -md sha256 -pass file:"$PASSFILE" > PKI.tar.gz.enc

  output "The file PKI.tar.gz.enc contains the PKI bundle."
  output "Bundle password written to ${PASSFILE} (mode 600), store it securely."
  output "Decryption can be done with below:"
  printf "%s\\n" "openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -md sha256 -pass file:${PASSFILE} -in PKI.tar.gz.enc -out PKI.tar.gz"
  printf "%s\\n" "mkdir PKI && tar -xzf PKI.tar.gz -C PKI"
  return 0
}

function verify_all() {
  #@ DESCRIPTION: Verify CA chain, CRLs, and all leaf certs (server + client)
  #@ USAGE: verify_all
  #@ REQUIREMENTS: openssl find grep awk sed grep

  local -r CHAIN="intermediateCA/certs/ca-chain.cert.pem"
  local -r INT_CERT="intermediateCA/certs/intermediate.cert.pem"
  local -r INT_CRL="intermediateCA/crl/intermediate.crl.pem"
  local -r ROOT_CERT="rootCA/certs/ca.cert.pem"
  local -r ROOT_CRL="rootCA/crl/ca.crl.pem"

  [[ -f "$CHAIN" ]]     || die 1 "Missing CA chain: $CHAIN"
  [[ -f "$INT_CERT" ]]  || die 1 "Missing intermediate cert: $INT_CERT"
  [[ -f "$INT_CRL" ]]   || die 1 "Missing intermediate CRL: $INT_CRL"

  # Root assets are only present in init bundles (rotate bundles may omit rootCA)
  if [[ -f "$ROOT_CERT" ]]; then
    output "Root cert present: $ROOT_CERT"
    [[ -f "$ROOT_CRL" ]] && output "Root CRL present: $ROOT_CRL"
  else
    output "Root cert not present (ok if this is a rotate bundle)."
  fi

  output "Verifying intermediate cert against chain"
  openssl verify -CAfile "$CHAIN" "$INT_CERT" >/dev/null 2>&1 \
    || die 12 "Intermediate cert verification failed: $INT_CERT"

  output "Checking CRL nextUpdate (intermediate)"
  openssl crl -in "$INT_CRL" -noout -lastupdate -nextupdate \
    || die 12 "Failed reading intermediate CRL: $INT_CRL"

  # Verify leaf certs with purpose + CRL checking
  output "Verifying leaf certs (purpose + CRL)"
  local failed=0

  # Servers
  for server in "${SERVERS[@]}"; do
    local cert="intermediateCA/certs/${server}.${SERVER_DOMAIN}.cert.pem"
    [[ -f "$cert" ]] || die 12 "Missing server cert: $cert"

    # Chain + purpose + CRL
    openssl verify -CAfile "$CHAIN" -purpose sslserver -crl_check -CRLfile "$INT_CRL" "$cert" >/dev/null 2>&1 \
      || { printf "FAIL sslserver: %s\n" "$cert" >&2; failed=1; }

    # SAN check (more stable than -text)
    openssl x509 -in "$cert" -noout -ext subjectAltName 2>/dev/null | grep -q "DNS:${server}.${SERVER_DOMAIN}" \
      || { printf "FAIL SAN missing DNS:%s.%s\n" "$server" "$SERVER_DOMAIN" >&2; failed=1; }

    # Expiry
    openssl x509 -in "$cert" -noout -subject -enddate
  done

  # Clients
  for key in "${!CLIENTS[@]}"; do
    local cert="intermediateCA/certs/${key}.client.cert.pem"
    [[ -f "$cert" ]] || die 12 "Missing client cert: $cert"

    openssl verify -CAfile "$CHAIN" -purpose sslclient -crl_check -CRLfile "$INT_CRL" "$cert" >/dev/null 2>&1 \
      || { printf "FAIL sslclient: %s\n" "$cert" >&2; failed=1; }

    # Email SAN check
    openssl x509 -in "$cert" -noout -ext subjectAltName 2>/dev/null | grep -qi "email:${CLIENTS[$key]}" \
      || { printf "FAIL SAN missing email:%s (%s)\n" "${CLIENTS[$key]}" "$cert" >&2; failed=1; }

    openssl x509 -in "$cert" -noout -subject -enddate
  done

  (( failed == 0 )) || die 12 "One or more verifications failed."
  output "All verifications passed."
  return 0
}


function main() {
  #@ DESCRIPTION:  main program loop
  #@ USAGE:  main "$@"

  if (( $# != 1 )) ; then
    usage
    echo ""
    die 7 "Command Line argument missing."
  else

  case "${1}" in
    init) mode=init ;;
    rotate) mode=rotate ;;
    verify) mode=verify ;;
    *) die 8 "${1} is not a valid option (init | rotate)." ;;
  esac
  fi

  cli_check
  env_check

  if [[ "$mode" == "init" ]]; then
    local -r CWD="$(pwd)"
    local -r WORKING_DIRECTORY="$(mktemp -d)"
    chmod 700 "$WORKING_DIRECTORY"

    cd "$WORKING_DIRECTORY" || die 6 "Could not cd to directory ${WORKING_DIRECTORY}."
    output "Starting init process; working directory is ${WORKING_DIRECTORY}"
    gen_folders
    output "Generating root CA/Key"
    gen_root_ca
    output "Generating intermediary CA/Key"
    gen_intermediary_ca
    output "Generating Server CA/KEY (keys are not encrypted)"
    gen_server_ca
    output "Generating Client CA/KEY (keys are not encrypted)"
    gen_client_ca
    output "Generating Root CRL"
    gen_crls_root
    output "Generating Intermediate CRL"
    gen_crls_intermediate

    output "Bundling PKI files into an encrypted tarball."
    cd "$CWD" || die 6 "Could not cd to directory ${CWD}."
    create_bundle "$WORKING_DIRECTORY"
    rm -rf "$WORKING_DIRECTORY"

  elif [[ "$mode" == "rotate" ]]; then
    require_existing_pki
    Verify_INTERMEDIATE_CA_PASSWORD

    output "Starting rotate process in $(pwd)"
    output "Archiving existing leaf material"
    archive_leaf_material

    output "Revoking archived leaf certificates (reason: superseded)"
    revoke_archived_leaf_certs

    output "Generating new Server certs/keys (keys are not encrypted)"
    gen_server_ca

    output "Generating new Client certs/keys (keys are not encrypted)"
    gen_client_ca

    output "Generating Intermediate CRL"
    gen_crls_intermediate
  elif [[ "$mode" == "verify" ]]; then
    require_existing_pki
    verify_all
  else
    die 9 "Invalid mode in main: ${mode}."
  fi
  return 0
}

main "$@"
exit 0
