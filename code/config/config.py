"""
Validated configuration model for the AI Improv Toolkit. Makes use of pydantic for validation.
"""

from typing import NamedTuple, Literal, Any
from pydantic import BaseModel, ConfigDict, PositiveInt, model_validator
import tomllib

AllowedActions = Literal["reset", "speak"]

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
]

_ComponentRole = Literal[
    "ingest",
    "vision",
    "hearing",
    "brain",
    "output",
    "health_check",
]


class ButtonResetSubSettings(NamedTuple):
    """
    Settings for the reset button.
    """

    Path: str
    Key: KeyOptions
    grab: bool  # wether the button will be grabbed for exclusive use.


class _AIAvatarSubSettings(NamedTuple):
    """
    Instructions for the AI avatar.
    """

    Instructions: str


class ButtonAvatarSubSettings(NamedTuple):
    """
    Settings for the avatar button.
    """

    Path: str
    Speak: KeyOptions
    grab: bool  # wether the button will be grabbed for exclusive use.


class _ShowSettings(NamedTuple):
    """
    Settings related to the overall show configuration.
    """

    Name: str
    Language: Literal["en-US"]
    Actors_count: PositiveInt
    Avatar_count: PositiveInt
    Show_length: PositiveInt  # in minutes
    Type: Literal["mono-scene"]
    Show_rating: Literal[
        "g", "pg", "pg-13", "r", "nc-17"
    ]  # Note: limited to pg-13 in Ethic mode.
    Disclaimer: Literal[
        "none", "short", "full"
    ]  # Note: must be short or full in Ethic mode.
    Command_keyword: str  # Keyword to activate voice commands.


class _AISettings(NamedTuple):
    """
    Settings related to AI behavior and instructions.
    """

    Introduction_instructions: str
    General_instructions: str
    show_watcher_instructions: str
    Avatars: list[_AIAvatarSubSettings]  # List of avatar settings


class _ModeSettings(NamedTuple):
    """
    Settings that control operational modes like Ethics mode and Debug mode.
    """

    Ethic: bool
    Debug: bool
    Role: _ComponentRole  # Role of the component


class _ButtonSettings(NamedTuple):
    """
    Settings related to button configurations.
    """

    Reset: ButtonResetSubSettings
    Avatars: list[ButtonAvatarSubSettings]


class _NetworkSettings(NamedTuple):
    """
    Settings related to network configurations.
    Not all user will need server certs/keys, but they are included here for completeness.
    """

    Nats_server: str
    Hearing_server: str
    Ca_cert_path: str
    Connection_timeout_s: PositiveInt
    Retry_attempts: PositiveInt
    Retry_backoff_ms: PositiveInt
    Use_tls: bool


class _HealthCheckSettings(NamedTuple):
    Enabled: bool
    Interval_seconds: PositiveInt


# @dataclasses.dataclass(frozen=True)
class Config(BaseModel):
    """
    Validated configuration model for the AI Improv Toolkit.
    Currently enforces MVP limitations:
    """

    model_config = ConfigDict(extra="forbid")
    Show: _ShowSettings
    AI: _AISettings
    Mode: _ModeSettings
    Buttons: _ButtonSettings
    Network: _NetworkSettings
    Health_Check: _HealthCheckSettings

    @model_validator(mode="after")
    def validate_mvp_limits(self):
        # Enforce MVP limitations
        if self.Show.Language != "en-US":
            raise ValueError("Only 'en-US' language is supported in MVP.")
        if self.Show.Type != "mono-scene":
            raise ValueError("Only 'mono-scene' show type is supported in MVP.")
        if self.Show.Actors_count != 1:
            raise ValueError("Only 1 actor is supported in MVP.")
        if self.Show.Avatar_count != 1:
            raise ValueError("Only 1 avatar is supported in MVP.")
        return self

    @model_validator(mode="after")
    def validate_avatars_count(self):
        if len(self.Buttons.Avatars) != self.Show.Avatar_count:
            raise ValueError("Buttons.Avatar count must match Show.Avatar_count.")
        if len(self.AI.Avatars) != self.Show.Avatar_count:
            raise ValueError("AI.Avatar count must match Show.Avatar_count.")
        return self

    @model_validator(mode="after")
    def validate_ethic_mode(self):
        if self.Mode.Ethic:
            if self.Show.Show_rating not in ["g", "pg", "pg-13"]:
                raise ValueError("In Ethic mode, Show_rating must be g, pg, or pg-13.")
            if self.Show.Disclaimer not in ["short", "full"]:
                raise ValueError("In Ethic mode, Disclaimer must be short or full.")
            if self.Mode.Debug:
                raise ValueError(
                    "Ethic mode and Debug mode cannot be enabled simultaneously."
                )
            if self.Network.Use_tls is not True:
                raise ValueError("TLS must be enabled in Ethics mode.")
        return self

    @model_validator(mode="after")
    def validate_buttons(self):
        """Validate that all configured button paths are unique."""
        paths = set()
        for button in self.Buttons.Avatars:
            if button.Path in paths:
                raise ValueError(f"Duplicate button path found: {button.Path}")
            paths.add(button.Path)
        if self.Buttons.Reset.Path in paths:
            raise ValueError(f"Duplicate button path found: {self.Buttons.Reset.Path}")
        return self


def generate_config(configPath: str) -> Config:
    """
    Generates a Config object from a TOML configuration file.
    Any raised validation errors will be propagated to the caller.

    :param configPath: Path to the configuration file
    :type configPath: str
    :return: Valid config object for the AI Improv Toolkit
    :rtype: Config
    """

    unverified_config: dict[str, Any]

    with open(configPath, mode="rb") as fp:
        unverified_config = tomllib.load(fp)

    return Config(**unverified_config)
