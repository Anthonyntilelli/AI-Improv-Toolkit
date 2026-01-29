#!/usr/bin/env bash
################ Script metadata ###############################################
#: Title        : silence_threshold.sh
#: Author       : Anthony Tilelli
#: Description  : Listen to the audio input and determine the silence threshold.
#:              : This output can be used to set the silence_threshold value in
#:              : the config.toml.
#: Usage        : ./silence_threshold.sh
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

set_up_venv_and_find_rms() {
  #@ DESCRIPTION:  Sets up a virtualenv in .venv
  #@ USAGE:  setup_venv
  #@ REQUIREMENTS: virtualenv installed

  # shellcheck disable=SC2155
  local directory="$(mktemp -d)"
  cd "$directory" || die 5 "Could not change tmp directory."
  virtualenv --no-setuptools  -p python3 venv > /dev/null || die 5 "Could not create virtualenv."
  . ./venv/bin/activate || die 5 "Could not activate virtualenv."

  output "This script lists average RMS values for audio input to help determine a suitable silence threshold."
  output "RMS can vary based on microphone sensitivity and environment."
  output "Mic must be connected and available when running this script."
  output "Working to install packages sounddevice and numpy. stand by..."
  pip --no-cache-dir install sounddevice numpy > /dev/null || die 5 "Could not install sounddevice and or numpy package"
  find_rms || die 5 "Could not find RMS values."
  cd - > /dev/null || die 5 "Could not return to previous directory."

  deactivate || die 5 "Could not deactivate virtualenv."
  rm -rf "$directory"
  return 0
}

find_rms() {
  #@ DESCRIPTION:  finds RMS values for audio input
  #@ USAGE:  find_rms
  #@ REQUIREMENTS: sounddevice package installed in active virtualenv
  output "------------------------------------------------------------"
  python3 - <<'EOF'
import sounddevice as sd, numpy as np
print("Recording audio for RMS calculation (using default mic), please be silent...")
try:
  d = sd.rec(int(16000*2), samplerate=16000, channels=1, dtype='float32'); sd.wait()
  print(f"Average RMS after 2 seconds: {np.sqrt(np.mean(d**2))}")
  d = sd.rec(int(16000*5), samplerate=16000, channels=1, dtype='float32'); sd.wait()
  print(f"Average RMS after 5 seconds: {np.sqrt(np.mean(d**2))}")
  print("Done. You can adjust the silence_threshold value in config.toml based on these RMS values, Be sure to round down.")
except Exception as e:
  print(f"An error occurred while recording audio: {e}")
EOF
  output "------------------------------------------------------------"
  return 0
}

main() {
  #@ DESCRIPTION:  Main function
  #@ USAGE:  main
  #@ REQUIREMENTS: NONE

  env_check
  set_up_venv_and_find_rms

  return 0
}

main "$@"
exit 0
