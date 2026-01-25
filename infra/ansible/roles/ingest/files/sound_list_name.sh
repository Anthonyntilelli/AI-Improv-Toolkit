#!/usr/bin/env bash
################ Script metadata ###############################################
#: Title        : sound_list_name
#: Author       : Anthony Tilelli
#: Description  : Lists available audio input devices using the sounddevice Python library.
#:              : This outout can be used to set the Actor.mic section in the config.yaml
#: Requirements : BASH 5.0+
#:              : Apt Packages: portaudio19-dev, libasound2-dev
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

  if [[ ! -d /dev/snd ]]; then
    die 4 "/dev/snd is not present. If running in Docker, pass --device /dev/snd."
  fi

  return 0
}

set_up_venv_and_list_devices() {
  #@ DESCRIPTION:  Sets up a virtualenv in .venv
  #@ USAGE:  setup_venv
  #@ REQUIREMENTS: virtualenv installed

  # shellcheck disable=SC2155
  local directory="$(mktemp -d)"
  cd "$directory" || die 5 "Could not change tmp directory."
  virtualenv --no-setuptools  -p python3 venv > /dev/null || die 5 "Could not create virtualenv."
  . ./venv/bin/activate || die 5 "Could not activate virtualenv."
  pip install sounddevice > /dev/null || die 5 "Could not install sounddevice package"
  cd - > /dev/null || die 5 "Could not return to previous directory."
  list_audio_devices || die 5 "Could not list audio devices."
  deactivate || die 5 "Could not deactivate virtualenv."
  rm -rf "$directory"
  return 0
}

list_audio_devices() {
  #@ DESCRIPTION:  Lists audio input devices using sounddevice
  #@ USAGE:  list_audio_devices
  #@ REQUIREMENTS: sounddevice package installed in active virtualenv
  output "This script lists available audio input devices using the sounddevice Python library."
  output "Devices listed here can be used to set the Actor.mic section in the config.yaml"
  output "Devices must be connected and available when running this script."
  output "------------------------------------------------------------"
  python3 - <<'EOF'
import sounddevice as sd
count = 0
deny = ("default", "sysdefault", "dmix", "front", "surround", "iec958", "spdif")
print("Input devices (PortAudio/sounddevice):")
for i, d in enumerate(sd.query_devices()):
    if d["max_input_channels"] <= 0:
        continue
    name = d["name"]
    name_l = name.lower()
    if any(x in name_l for x in deny):
        continue
    print(f'- "{name}", sample_rate={d["default_samplerate"]}, max_input_channels={d["max_input_channels"]}')
    count += 1
if count == 0:
    print("No input devices found. Check /dev/snd permissions and audio group membership.")
EOF
  output "------------------------------------------------------------"
  return 0
}

main() {
  #@ DESCRIPTION:  Main function
  #@ USAGE:  main
  #@ REQUIREMENTS: NONE

  env_check
  set_up_venv_and_list_devices

  return 0
}

main "$@"
exit 0
