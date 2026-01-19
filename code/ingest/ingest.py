"""
Ingest role module.
Use the main function to start the ingest process.
"""

# HID API documentation: https://trezor.github.io/cython-hidapi/api.html

from typing import Any #, Generator
from dataclasses import dataclass
# from contextlib import contextmanager
from time import sleep

# import evdev # HID is not used any more need to switch to event-based input

from config import KeyOptions as KO
# from config import ButtonResetSubSettings as RBC
# from config import ButtonAvatarSubSettings as BAC
from config import config as cfg
# from ._config import load_internal_config, _AudioSettings as AudioSettings


@dataclass
class ResetButton:
    device: Any # TODO: specify type
    path: str
    key: KO
    last_pressed: int = 0
    is_open: bool = False


@dataclass
class AvatarButton:
    device: Any # TODO: specify type
    path: str
    key_speak: KO
    key_uncomfortable: KO
    key_humor: KO
    last_pressed: int = 0
    is_open: bool = False

# HID Raw Input is not used any more need to switch to event-based input
# @contextmanager
# def managed_reset_button(resetConfig: RBC) -> Generator[ResetButton, None, None]:
#     """Context manager for HID reset button device."""
#     path = resetConfig["Path"]
#     key = resetConfig["Key"]
#     reset_button: ResetButton = ResetButton(hid.device(), path, key)
#     try:
#         reset_button.device.open_path(reset_button.path)
#         reset_button.is_open = True
#         yield reset_button
#     finally:
#         if reset_button.is_open:
#             reset_button.device.close()
#             reset_button.is_open = False


# @contextmanager
# def managed_avatar_button(avatarConfig: BAC) -> Generator[AvatarButton, None, None]:
#     """Context manager for HID avatar button device."""
#     path = avatarConfig["Path"]
#     key_speak = avatarConfig["Speak"]
#     key_uncomfortable = avatarConfig["Speak_uncomfortable"]
#     key_humor = avatarConfig["Speak_humor"]
#     avatar_button: AvatarButton = AvatarButton(
#         hid.device(), path, key_speak, key_uncomfortable, key_humor
#     )
#     try:
#         avatar_button.device.open_path(avatar_button.path)
#         avatar_button.is_open = True
#         yield avatar_button
#     finally:
#         if avatar_button.is_open:
#             avatar_button.device.close()
#             avatar_button.is_open = False


def main(config: cfg.Config) -> None:
    """Main function to start the ingest role."""
    print("Ingest role started.")

    # reset_config: AudioSettings = load_internal_config(config.Show["Actors_count"])
    # avatar_count = len(config.Buttons["Avatars"])

    sleep(5)

    print("Ingest role completed.")
