#!/usr/bin/env bash
################ Script metadata ###############################################
#: Title        : list_and_monitor.sh
#: Author       : Anthony Tilelli
#: Description  : This script will list all inputs in the /dev/input/by-id/ directory
#:              : and monitor button presses on the selected input device.
#:              : This output can be used to identify button codes for configuration.
#: Usage        : ./list_and_monitor.sh
#: Requirements : BASH 5.0+
#:              : pip
#:              : virtualenv
#:              :
#: Version      : 0.0.1 (https://semver.org/)
#: ExitCodes    : (reserved https://www.tldp.org/LDP/abs/html/exitcodes.html)
#:              : 0 "Success"
#:              : 1 General Failure (varied message)
#:              : 3 Bash-5.0+ is required to run this script
#:              : 4 Missing required env items (varied message)
#:              : 5 Setup of virtualenv failed (varied message)
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

#Function
function die() {
  #@ DESCRIPTION:  prints error-message and exits script
  #@ USAGE:  die ERRORCODE ERROR_MESSAGE or die
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

env_check() {
  #@ DESCRIPTION:  Check if needed items are in place.
  #@ USAGE:  env_check
  #@ REQUIREMENTS: NONE

  if ! command -v python3 &> /dev/null
  then
    die 4 "python3 is missing, Install it please, and then run this tool again."
  fi

  if ! command -v pip &> /dev/null
  then
    die 4 "pip is missing, Install it please, and then run this tool again."
  fi

  if ! command -v virtualenv &> /dev/null
  then
    die 4 "virtualenv is missing, Install it please, and then run this tool again."
  fi

  if [[ ! -d /dev/input ]]; then
    die 4 "/dev/input is not present. If running in Docker, pass --device=/dev/input."
  fi

  return 0
}

set_up_venv_and_find_python() {
  #@ DESCRIPTION:  Sets up a virtualenv in .venv and runs the python script.
  #@ USAGE:  setup_venv
  #@ REQUIREMENTS: virtualenv installed

  # shellcheck disable=SC2155
  local directory="$(mktemp -d)"
  cd "$directory" || die 5 "Could not change to temporary directory: $directory"
  virtualenv --no-setuptools  -p python3 venv > /dev/null || die 5 "Could not create virtualenv."
  . ./venv/bin/activate || die 5 "Could not activate virtualenv."

  output "This script will list all input devices in /dev/input/by-id/ and monitor button presses."
  output "All devices must be connected before running this script."
  output "Working to install package evdev. stand by..."
  pip --no-cache-dir install evdev > /dev/null || die 5 "Could not install evdev package"
  find_inputs || die 5 "Could not find inputs."
  cd - > /dev/null || die 5 "Could not return to previous directory."

  deactivate || die 5 "Could not deactivate virtualenv."
  rm -rf "$directory"
  return 0
}

find_inputs() {
  #@ DESCRIPTION:  list and monitor button presses
  #@ USAGE:  find_inputs
  #@ REQUIREMENTS: evdev package installed in active virtualenv
  output "------------------------------------------------------------"
  python3 - <<'EOF'
from pathlib import Path
import evdev
print("Listing all input devices in /dev/input/by-id/. Each id is a symlink to /dev/input/eventX.")
print("In config, it is best to use the /dev/input/by-id/ path to avoid issues with eventX changing.")
by_id = Path("/dev/input/by-id")
for link in sorted(by_id.iterdir()):
  if link.is_symlink():
    try:
      target = link.readlink()
      resolved = link.resolve()
      print(f"{link} -> {target} (resolved: {resolved})")
    except OSError as e:
      print(f"Skipping link {link} error accessing: {e}")
print("Invoking evdev to monitor button presses. Please select the device path to monitor (e.g., /dev/input/eventX):")
EOF
  python -m evdev.evtest
  output "------------------------------------------------------------"
  return 0
}

main() {
  #@ DESCRIPTION:  Main function
  #@ USAGE:  main
  #@ REQUIREMENTS: NONE

  env_check
  set_up_venv_and_find_python

  return 0
}

main "$@"
exit 0
