"""
Creates the ingestion configuration model and loads the internal.toml file and general config.
Ingests general configuration from config.Config to create IngestSettings.
All setting needed for ingestion are defined here.
"""

from typing import Any, Literal, NamedTuple
import os
from pathlib import Path
from common.dataTypes import ButtonActions

from pydantic import BaseModel, PositiveInt, ConfigDict, model_validator
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


class _ResetButton(BaseModel):
    path: str
    reset: KeyOptions
    grab: bool


class _ControllerConfig(BaseModel):
    path: str
    speak: KeyOptions
    exit: KeyOptions
    grab: bool


class _MicConfig(BaseModel):
    """Configuration settings for individual microphones."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    channel_handling: Literal["mono", "split_all", "downmix_to_mono"]

    @model_validator(mode="after")
    def validate_channel_handling(cls, self):
        device = sd.query_devices(self.name, "input", kind="input")  # Validate mic exists and is an input device
        if device is None:
            raise ValueError(f"Microphone device '{self.name}' not found.")
        if self.channel_handling == "mono":
            if device["max_input_channels"] != 1:
                raise ValueError(f"Microphone '{self.name}' is not a mono device.")
        elif self.channel_handling == "split_all":
            if device["max_input_channels"] < 2:
                raise ValueError(f"Microphone '{self.name}' does not have multiple channels to split.")
        elif self.channel_handling == "downmix_to_mono":
            if device["max_input_channels"] < 2:
                raise ValueError(f"Microphone '{self.name}' does not have multiple channels to downmix.")
        return self


class ButtonConfig(NamedTuple):
    """Configuration settings for input buttons (reset or avatar)."""

    path: str
    keys: dict[KeyOptions, ButtonActions]
    grab: bool
    avatar_id: int  # -1 is control button, 0..n are avatar buttons


class FrontendConfig(BaseModel):
    """Configuration settings for the frontend role portion of the configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    button_debounce_ms: PositiveInt
    webrtc_id: str
    reset: ButtonConfig
    mics: list[_MicConfig]
    controllers: list[ButtonConfig]

    @model_validator(mode="before")
    def set_button_actions(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Set button actions based on their role in the configuration."""
        if not isinstance(values, dict):
            raise ValueError("set_button_actions function failed: values must be a dictionary.")

        pre_reset = _ResetButton(**values.get("reset", {}))
        pre_controllers = [_ControllerConfig(**ctrl) for ctrl in values.get("controllers", [])]
        if len(pre_controllers) == 0:
            raise ValueError("At least one controller must be defined in the frontend configuration.")

        values["reset"] = ButtonConfig(
            path=pre_reset.path,
            keys={pre_reset.reset: "reset"},
            grab=pre_reset.grab,
            avatar_id=-1,
        )
        values["controllers"] = []
        for idx, ctrl in enumerate(pre_controllers):
            ctrl_config = ButtonConfig(
                path=ctrl.path, keys={ctrl.speak: "speak", ctrl.exit: "exit"}, grab=ctrl.grab, avatar_id=idx
            )
            values["controllers"].append(ctrl_config)
        return values

    @model_validator(mode="after")
    def validate_buttons(cls, values):
        buttons_paths = [values.reset.path] + [button.path for button in values.controllers]
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
    def mvp_limitations(cls, values):
        """Validate settings against MVP limitations."""
        if not values.controllers or len(values.controllers) != 1:
            raise ValueError("MVP limitation: Only one avatar button is supported.")
        if not values.mics or len(values.mics) != 1:
            raise ValueError("MVP limitation: Exactly 1 actor microphone is required.")
        return values
