"""
Creates the ingestion configuration model and loads the internal.toml file and general config.
Ingests general configuration from config.Config to create IngestSettings.
All setting needed for ingestion are defined here.
"""

from typing import Any, Literal, NamedTuple
import re
import os
from pathlib import Path
from common.dataTypes import ButtonActions

from pydantic import BaseModel, PositiveFloat, PositiveInt, ConfigDict, model_validator
import sounddevice as sd

# Define the valid key options (as seen by evdev)
# Limited to Us English keyboard keys without modifiers.
KeyOptions = Literal[
    "KEY_ESC",
    "KEY_1",
    "KEY_2",
    "KEY_3",
    "KEY_4",
    "KEY_5",
    "KEY_6",
    "KEY_7",
    "KEY_8",
    "KEY_9",
    "KEY_0",
    "KEY_MINUS",
    "KEY_EQUAL",
    "KEY_BACKSPACE",
    "KEY_TAB",
    "KEY_Q",
    "KEY_W",
    "KEY_E",
    "KEY_R",
    "KEY_T",
    "KEY_Y",
    "KEY_U",
    "KEY_I",
    "KEY_O",
    "KEY_P",
    "KEY_LEFTBRACE",
    "KEY_RIGHTBRACE",
    "KEY_ENTER",
    "KEY_A",
    "KEY_S",
    "KEY_D",
    "KEY_F",
    "KEY_G",
    "KEY_H",
    "KEY_J",
    "KEY_K",
    "KEY_L",
    "KEY_SEMICOLON",
    "KEY_APOSTROPHE",
    "KEY_GRAVE",
    "KEY_BACKSLASH",
    "KEY_Z",
    "KEY_X",
    "KEY_C",
    "KEY_V",
    "KEY_B",
    "KEY_N",
    "KEY_M",
    "KEY_COMMA",
    "KEY_DOT",
    "KEY_SLASH",
    "KEY_SPACE",
    "KEY_F1",
    "KEY_F2",
    "KEY_F3",
    "KEY_F4",
    "KEY_F5",
    "KEY_F6",
    "KEY_F7",
    "KEY_F8",
    "KEY_F9",
    "KEY_F10",
    "KEY_F11",
    "KEY_F12",
    "KEY_HOME",
    "KEY_UP",
    "KEY_PAGEUP",
    "KEY_LEFT",
    "KEY_RIGHT",
    "KEY_END",
    "KEY_DOWN",
    "KEY_PAGEDOWN",
    "KEY_INSERT",
    "KEY_DELETE",
    "KEY_KP0",
    "KEY_KP1",
    "KEY_KP2",
    "KEY_KP3",
    "KEY_KP4",
    "KEY_KP5",
    "KEY_KP6",
    "KEY_KP7",
    "KEY_KP8",
    "KEY_KP9",
    "KEY_KPDOT",
    "KEY_KPENTER",
    "KEY_KPMINUS",
    "KEY_KPPLUS",
    "KEY_KPASTERISK",
    "KEY_KPSLASH",
]


class ButtonConfig(NamedTuple):
    """Configuration settings for input buttons (reset or avatar)."""

    path: str
    key: KeyOptions
    grab: bool
    action: ButtonActions


class ActorMicsConfig(NamedTuple):
    """Configuration settings for the actor microphones."""

    name: str
    use_noise_reducer: bool


class IngestSettings(BaseModel):
    """Configuration settings for the ingestion role portion of the configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    audio_chunks_ms: Literal[10, 20, 30]
    vad_aggressiveness: Literal[0, 1, 2, 3]
    button_debounce_ms: PositiveInt
    silence_threshold: PositiveFloat
    hearing_server: str
    reset: ButtonConfig
    avatar_controllers: list[ButtonConfig]
    actor_mics: list[ActorMicsConfig]

    @model_validator(mode="after")
    def validate_hearing_server(cls, values):
        """Validate that the hearing server is properly formatted."""
        server = values.hearing_server
        hearing_pattern = re.compile(r"^[a-zA-Z0-9.-_]+:\d{1,5}$")
        if not hearing_pattern.match(server):
            raise ValueError(f"Hearing server '{server}' is not in the correct format 'hostname:port'")
        return values

    @model_validator(mode="before")
    @classmethod
    def set_button_actions(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Set button actions based on their role in the configuration."""
        if not isinstance(values, dict):
            raise ValueError("set_button_actions function failed: values must be a dictionary.")

        reset = values.get("reset")
        if reset:
            values["reset"] = ButtonConfig(
                path=reset.get("path"),
                key=reset.get("key"),
                grab=reset.get("grab"),
                action="reset",  # computed or derived
            )
        avatar_controllers = values.get("avatar_controllers")
        if avatar_controllers:
            values["avatar_controllers"] = [
                ButtonConfig(
                    path=button.get("path"),
                    key=button.get("key"),
                    grab=button.get("grab"),
                    action="speak",
                )
                for button in avatar_controllers
            ]
        return values

    @model_validator(mode="after")
    def validate_button_actions(cls, values):
        """Validate that button actions are correctly assigned."""
        for button in values.avatar_controllers:
            if button.action != "speak":
                raise ValueError(f"Avatar controller button at path {button.path} does not have action 'speak'.")
        if values.reset.action != "reset":
            raise ValueError(f"Reset button at path {values.reset.path} does not have action 'reset'.")
        return values

    @model_validator(mode="after")
    def validate_buttons(cls, values):
        buttons_paths = [values.reset.path] + [button.path for button in values.avatar_controllers]
        button_set = set(buttons_paths)
        if len(button_set) != len(buttons_paths):
            raise ValueError("Duplicate button device paths found in reset and avatar buttons.")
        for button in buttons_paths:
            p = Path(button)
            if not p.exists():
                raise ValueError(f"Button device path {p} does not exist.")
            if not p.is_char_device():
                raise ValueError(f"Button device path {p} is not a character device.")

            flags = os.O_RDONLY | os.O_NONBLOCK  # Open in non-blocking read-only mode (to avoid blocking if grabbed)
            try:
                fd = os.open(button, flags)
                os.close(fd)
            except OSError as e:
                raise ValueError(f"Button device path {button} is not accessible: {e}")
        return values

    @model_validator(mode="after")
    def validate_actor_mics(cls, values):
        mic_names = set([mic.name for mic in values.actor_mics])
        if len(mic_names) != len(values.actor_mics):
            raise ValueError("Duplicate microphone names found in actor microphones.")

        for mic in values.actor_mics:
            try:
                sd.check_input_settings(device=mic.name)
            except sd.PortAudioError as e:
                raise ValueError(f"Microphone device '{mic.name}' is not accessible: {e}")
        return values

    @model_validator(mode="after")
    def mvp_limitations(cls, values):
        """Validate settings against MVP limitations."""
        if not values.avatar_controllers or len(values.avatar_controllers) != 1:
            raise ValueError("MVP limitation: Only one avatar button is supported.")
        if not values.actor_mics or len(values.actor_mics) != 1:
            raise ValueError("MVP limitation: Exactly 1 actor microphone is required.")
        return values
