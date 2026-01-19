"""
Ingest role module.
Use the main function to start the ingest process.
"""

# evdev API reference: https://python-evdev.readthedocs.io/en/latest/usage.html

from dataclasses import dataclass
from time import sleep

import evdev

from config import KeyOptions as KO
# from config import ButtonResetSubSettings as RBC
# from config import ButtonAvatarSubSettings as BAC
from config import config as cfg
# from ._config import load_internal_config, _AudioSettings as AudioSettings

@dataclass
class Button:
    device: evdev.InputDevice
    path: str
    key: dict[KO, str] # key with action name
    grabbed: list[bool]
    last_pressed: int = 0


def main(config: cfg.Config) -> None:
    """Main function to start the ingest role."""
    print("Ingest role started.")

    # reset_config: AudioSettings = load_internal_config(config.Show["Actors_count"])
    # avatar_count = len(config.Buttons["Avatars"])

    sleep(5)

    print("Ingest role completed.")
