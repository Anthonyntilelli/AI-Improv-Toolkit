"""
Validated configuration model for the AI Improv Toolkit. Makes use of pydantic for validation.
"""

import logging
from typing import NamedTuple, Literal, Any
from pydantic import BaseModel, ConfigDict, PositiveFloat, PositiveInt, model_validator
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

ComponentRole = Literal[
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


class AIAvatarSubSettings(NamedTuple):
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


class ShowSettings(NamedTuple):
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
    Silence_threshold: PositiveFloat  # Threshold for detecting silence (RMS)


class AISettings(NamedTuple):
    """
    Settings related to AI behavior and instructions.
    """

    Introduction_instructions: str
    General_instructions: str
    show_watcher_instructions: str
    Avatars: list[AIAvatarSubSettings]  # List of avatar settings


class ModeSettings(NamedTuple):
    """
    Settings that control operational modes like Ethics mode and Debug mode.
    """

    Ethic: bool
    Role: ComponentRole  # Role of the component
    Debug_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class ButtonSettings(NamedTuple):
    """
    Settings related to button configurations.
    """

    Reset: ButtonResetSubSettings
    Avatars: list[ButtonAvatarSubSettings]


class NetworkSettings(NamedTuple):
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


class HealthCheckSettings(NamedTuple):
    Enabled: bool
    Interval_seconds: PositiveInt


class MicsSubSettings(NamedTuple):
    """Holds microphone specific settings."""

    Mic_name: str


class ActorSettings(NamedTuple):
    """Holds actor specific settings."""

    Mics: list[MicsSubSettings]


# @dataclasses.dataclass(frozen=True)
class Config(BaseModel):
    """
    Validated configuration model for the AI Improv Toolkit.
    Currently enforces MVP limitations:
    """

    model_config = ConfigDict(extra="forbid")
    Show: ShowSettings
    AI: AISettings
    Mode: ModeSettings
    Buttons: ButtonSettings
    Network: NetworkSettings
    Health_Check: HealthCheckSettings
    Actors: ActorSettings

    @model_validator(mode="after")
    def validate_mvp_limits(self) -> "Config":
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
    def validate_avatars_count(self) -> "Config":
        if len(self.Buttons.Avatars) != self.Show.Avatar_count:
            raise ValueError("Buttons.Avatar count must match Show.Avatar_count.")
        if len(self.AI.Avatars) != self.Show.Avatar_count:
            raise ValueError("AI.Avatar count must match Show.Avatar_count.")
        return self

    @model_validator(mode="after")
    def validate_ethic_mode(self) -> "Config":
        if self.Mode.Ethic:
            if self.Show.Show_rating not in ["g", "pg", "pg-13"]:
                raise ValueError("In Ethic mode, Show_rating must be g, pg, or pg-13.")
            if self.Show.Disclaimer not in ["short", "full"]:
                raise ValueError("In Ethic mode, Disclaimer must be short or full.")
            if self.Mode.Debug_level in ["DEBUG", "INFO", "WARNING"]:
                raise ValueError(
                    "In Ethics mode, Debug_level cannot be DEBUG, INFO, or WARNING."
                )
            if self.Network.Use_tls is not True:
                raise ValueError("TLS must be enabled in Ethics mode.")
        return self

    @model_validator(mode="after")
    def validate_buttons(self) -> "Config":
        """Validate that all configured button paths are unique."""
        paths = set()
        for button in self.Buttons.Avatars:
            if button.Path in paths:
                raise ValueError(f"Duplicate button path found: {button.Path}")
            paths.add(button.Path)
        if self.Buttons.Reset.Path in paths:
            raise ValueError(f"Duplicate button path found: {self.Buttons.Reset.Path}")
        return self

    # TODO: MVP only supports only one mic per actor (future input with more mics)
    @model_validator(mode="after")
    def validate_actors_mics(self) -> "Config":
        """Validate that the Actors configurations are valid."""
        if len(self.Actors.Mics) != self.Show.Actors_count:
            raise ValueError("Number of Actors.Mics must match Show.Actors_count.")
        mic_set: set[str] = set()
        for mic in self.Actors.Mics:
            mic_set.add(mic.Mic_name)

        if len(mic_set) != len(self.Actors.Mics):
            raise ValueError("Duplicate mic names found in Actors.Mics.")

        return self

    @model_validator(mode="after")
    def validate_silence_threshold(self) -> "Config":
        """Validate that the silence threshold is within a reasonable range."""
        if not (0.0 < self.Show.Silence_threshold < 1.0):
            raise ValueError("Show.Silence_threshold must be between 0.0 and 1.0.")
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


def get_logging_level(config: Config) -> int:
    """Get the logging level based on the Debug_level setting."""
    level_mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_mapping[config.Mode.Debug_level]
