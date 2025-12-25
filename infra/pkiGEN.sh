#!/usr/bin/env bash
################ Script metadata ###############################################
#: Title        : PKI GEN
#: Author       : Anthony Tilelli
#: Description  : Generate the PKI certs and root certificate needed for the project
#: Requirements : BASH 5.0+
#:              : openssl
#:              : tar
#:              : mktemp
#: Options      :
#: ENV Variables:
#:              : ROOT_CA_PASSWORD <- Password For Root CA
#:              : INTERMEDIATE_CA_PASSWORD <- Password For intermediate CA
#: Version      : Major.minor.patch (https://semver.org/)
#: ExitCodes    : (reserved https://www.tldp.org/LDP/abs/html/exitcodes.html)
#:              : 0 "Success"
#:              : 1 General Failure (varied message)
#:              : 3 Bash-5.0+ is required to run this script
#:              : 4 <command> is missing, Install it please, and then run this tool again.
#:              : 5 <ENV Variable> is missing, please set it then run this tool again.
#:              : 6 Could not cd to directory <DIRECTORY>.
################ Script metadata ###############################################

# strict mode
# http://redsymbol.net/articles/unofficial-bash-strict-mode/
# https://disconnected.systems/blog/another-bash-strict-mode/
set -euo pipefail
IFS=$'\n\t'
# shellcheck disable=SC2154
trap 's=$?; echo "$0: Error on line "$LINENO": $BASH_COMMAND"; exit $s' ERR

# Version Check
if ((BASH_VERSINFO < 5))
then
  printf "Bash-5.0+ is required to run this script \\n" >&2
  exit 3
fi

# Constants
readonly GL_LOG="/dev/null"
readonly SERVER_DOMAIN="tilelli.me"


#Function
function die() {
  #@ DESCRIPTION:  prints error-message and exits script
  #@ USAGE:  die ERRORCODE ERROR_MESSAGE or die
  #@ REQUIREMENTS: NONE

  local -r ERRORCODE="${1:-1}"
  local -r ERROR_MESSAGE="${2:-"No \"ERROR_MESSAGE\" provided"}"
  local -r TIMESTAMP="$(date)"
  printf "FATAL %d: %s: %s\\n" "$ERRORCODE" "$TIMESTAMP" "$ERROR_MESSAGE" >&2
  printf "FATAL %d: %s: %s\\n" "$ERRORCODE" "$TIMESTAMP" "$ERROR_MESSAGE" >> "$GL_LOG"
  exit "$ERRORCODE"
}

function output() {
  #@ DESCRIPTION:  prints message
  #@ USAGE:  output <MESSAGE>
  #@ REQUIREMENTS: NONE

  local -r MESSAGE="${1:-"No \"MESSAGE\" provided"}"
  local -r TIMESTAMP="$(date)"
  printf "%s: (%s)\\n" "$MESSAGE" "$TIMESTAMP"
  printf "%s: (%s)\\n" "$MESSAGE" "$TIMESTAMP"  >> "$GL_LOG"
  return 0
}

function warn() {
  #@ DESCRIPTION:  prints message to stderr
  #@ USAGE:  warn <MESSAGE>
  #@ REQUIREMENTS: NONE

  local -r MESSAGE="${1:-"No \"MESSAGE\" provided"}"
  local -r TIMESTAMP="$(date)"
  printf "WARNING: %s (%s)\\n" "$MESSAGE" "$TIMESTAMP" >&2
  printf "WARNING: %s (%s)\\n" "$MESSAGE" "$TIMESTAMP" >> "$GL_LOG"
  return 0

}

function trim() {
  #@ SOURCE: https://stackoverflow.com/questions/369758/how-to-trim-whitespace-from-a-bash-variable
  #@ DESCRIPTION:  Removes leading and trailing spaces
  #@ USAGE:  trim <string>
  #@ REQUIREMENTS: NONE

  local trimmed="$1"

  # Strip leading spaces.
  while [[ $trimmed == ' '* ]]; do
      trimmed="${trimmed## }"
  done
  # Strip trailing spaces.
  while [[ $trimmed == *' ' ]]; do
      trimmed="${trimmed%% }"
  done

  echo "$trimmed"
}

function cli_check() {
  #@ DESCRIPTION:  Check if needed CLI commands are in place.
  #@ USAGE:  cli_check
  #@ REQUIREMENTS: NONE

  if ! command -v openssl &> /dev/null
  then
    die 4 "openssl is missing, Install it please, and then run this tool again."
  fi
  if ! command -v mktemp &> /dev/null
  then
    die 4 "mktemp is missing, Install it please, and then run this tool again."
  fi
  if ! command -v tar &> /dev/null
  then
    die 4 "tar is missing, Install it please, and then run this tool again."
  fi

  return 0
}

function env_check() {
  #@ DESCRIPTION:  Check if needed ENV Variable are in place.
  #@ USAGE:  env_check
  #@ REQUIREMENTS: NONE

  if ! [[ -v ROOT_CA_PASSWORD ]]; then
    die 5 "ROOT_CA_PASSWORD is missing, please set it then run this tool again."
  fi
  if ! [[ -v INTERMEDIATE_CA_PASSWORD ]]; then
    die 5 "INTERMEDIATE_CA_PASSWORD is missing, please set it then run this tool again."
  fi
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
  touch rootCA/index.txt
  touch intermediateCA/index.txt
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
nsCertType = server                                         # Server certificate type
keyUsage = critical, digitalSignature, keyEncipherment      # Key usage for a server cert
extendedKeyUsage = serverAuth                               # Extended key usage for server authentication purposes (e.g., TLS/SSL servers).
authorityKeyIdentifier = keyid,issuer                       # Authority key identifier linking the certificate to the issuer's public key.                               # Sets the SAN
EOF

  chmod 400 openssl_intermediate.cnf
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
  -subj "/C=US/ST=Pennsylvania/L=Mechanicsburg/O=Anthony/OU=Improv Show/CN=Root CA"

  chmod 444 rootCA/certs/ca.cert.pem
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
  -subj "/C=US/ST=Pennsylvania/L=Mechanicsburg/O=Anthony/OU=Improv Show/CN=Intermediate CA"

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
}

function gen_server_ca() {
  #@ DESCRIPTION: generated nats, hearing and vision server certifications in cwd assuming standard structure.
  #@ Warning: These certs are not password protected
  #@ USAGE: gen_server_ca
  #@ REQUIREMENTS: openssl

  local servers=(nats vision hearing)

  for server in "${servers[@]}" ; do
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -out intermediateCA/private/${server}.${SERVER_DOMAIN}.key.pem  2>/dev/null
    chmod 400 intermediateCA/private/${server}.${SERVER_DOMAIN}.key.pem

    openssl req -config openssl_intermediate.cnf \
      -key intermediateCA/private/${server}.${SERVER_DOMAIN}.key.pem \
      -new -sha256 -out intermediateCA/csr/${server}.${SERVER_DOMAIN}.csr.pem \
      -subj "/C=US/ST=Pennsylvania/L=Mechanicsburg/O=Anthony/OU=Improv Show/CN=${server}.${SERVER_DOMAIN}" \
      -addext "subjectAltName=DNS:${server}.${SERVER_DOMAIN},DNS:${SERVER_DOMAIN}"
    chmod 444 intermediateCA/csr/${server}.${SERVER_DOMAIN}.csr.pem

    openssl ca -config <(cat openssl_intermediate.cnf; cat <<EOF
[ server_cert ]
subjectAltName = @alt_names

[ alt_names ]
DNS.1 = ${server}.${SERVER_DOMAIN}
DNS.2 = ${SERVER_DOMAIN}
EOF
) \
      -extensions server_cert -days 375 -notext -md sha256  -batch \
      -in intermediateCA/csr/${server}.${SERVER_DOMAIN}.csr.pem \
      -passin env:INTERMEDIATE_CA_PASSWORD \
      -out intermediateCA/certs/${server}.${SERVER_DOMAIN}.cert.pem >/dev/null 2>&1

    chmod 444 intermediateCA/certs/${server}.${SERVER_DOMAIN}.cert.pem
  done
}

function gen_client_ca() {
  #@ DESCRIPTION: generated setting, nats_debug, ingest, vision, hearing, brain, output
  #@ client certifications in cwd assuming standard structure.
  #@ Warning: These certs are not password protected
  #@ USAGE: gen_client_ca
  #@ REQUIREMENTS: openssl

  local -A clients
  clients[setting]="setting@improvShow.local"
  clients[nats_debug]="nats_debug@improvShow.local"
  clients[ingest]="ingest@improvShow.local"
  clients[vision]="vision@improvShow.local"
  clients[hearing]="hearing@improvShow.local"
  clients[brain]="brain@improvShow.local"
  clients[output]="output@improvShow.local"

  for key in "${!clients[@]}"; do
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -out intermediateCA/private/${key}.client.key.pem  2>/dev/null
    chmod 400 intermediateCA/private/${key}.client.key.pem

    openssl req -config openssl_intermediate.cnf \
    -key intermediateCA/private/${key}.client.key.pem \
    -new -sha256 -out intermediateCA/csr/${key}.client.csr.pem \
    -subj "/C=US/ST=Pennsylvania/L=Mechanicsburg/O=Anthony/OU=Improv Show/CN=${key}.client" \
    -addext "subjectAltName=email:${clients[$key]}"
    chmod 444 intermediateCA/csr/${key}.client.csr.pem

    openssl ca \
    -config <(cat openssl_intermediate.cnf; cat <<EOF
[ server_cert ]
subjectAltName = @alt_names

[ alt_names ]
email = ${clients[$key]}
EOF
) \
    -extensions server_cert \
    -days 375 -notext -md sha256  -batch \
    -in intermediateCA/csr/${key}.client.csr.pem \
    -passin env:INTERMEDIATE_CA_PASSWORD \
    -out intermediateCA/certs/${key}.client.cert.pem >/dev/null 2>&1
    chmod 444 intermediateCA/certs/${key}.client.cert.pem
  done

}

function main() {
  #@ DESCRIPTION:  main program loop
  #@ USAGE:  main "$@"

  cli_check
  env_check

  local -r CWD="$(pwd)"
  local -r WORKING_DIRECTORY="$(mktemp -d)"
  chmod 700 "$WORKING_DIRECTORY"

  cd "$WORKING_DIRECTORY" || die 6 "Could not cd to directory ${WORKING_DIRECTORY}."
  gen_folders
  gen_root_ca
  gen_intermediary_ca
  gen_server_ca
  gen_client_ca

  cd "$CWD" || die 6 "Could not cd to directory ${CWD}."
  tar -czf PKI.tar.gz -C "$WORKING_DIRECTORY" .
  rm -rf ${WORKING_DIRECTORY}

  unset ROOT_CA_PASSWORD
  unset INTERMEDIATE_CA_PASSWORD
}

main "$@"
exit 0
