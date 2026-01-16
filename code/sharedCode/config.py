"""
Validated configuration model for the AI Improv Toolkit. Makes use of pydantic for validation.

e.g. from config import Config, generate_config
"""

from typing import TypedDict, Literal, Any
from pydantic import BaseModel, ConfigDict, PositiveInt, model_validator
import tomllib

# Define the valid key options
KeyOptions = Literal[
    "a",
    "b",
    "c",
    "d",
    "e",
    "f",
    "g",
    "h",
    "i",
    "j",
    "k",
    "l",
    "m",
    "n",
    "o",
    "p",
    "q",
    "r",
    "s",
    "t",
    "u",
    "v",
    "w",
    "x",
    "y",
    "z",
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    " ",
    "!",
    '"',
    "#",
    "$",
    "%",
    "&",
    "'",
    "(",
    ")",
    "*",
    "+",
    ",",
    "-",
    ".",
    "/",
    ":",
    ";",
    "<",
    "=",
    ">",
    "?",
    "@",
    "[",
    "\\",
    "]",
    "^",
    "_",
    "{",
    "|",
    "}",
    "~",
    "Tab",
    "Shift",
    "Ctrl",
    "Alt",
    "Space",
    "Enter",
    "Backspace",
    "Delete",
    "Insert",
    "Home",
    "End",
    "PageUp",
    "PageDown",
    "ArrowUp",
    "ArrowDown",
    "ArrowLeft",
    "ArrowRight",
    "Escape",
    "Pause",
    "F1",
    "F2",
    "F3",
    "F4",
    "F5",
    "F6",
    "F7",
    "F8",
    "F9",
    "F10",
    "F11",
    "F12",
]


class ButtonResetSubSettings(TypedDict):
    """
    Settings for the reset button.
    """

    Path: str
    Key: KeyOptions


class AIAvatarSubSettings(TypedDict):
    """
    Instructions for the AI avatar.
    """

    Instructions: str


class ButtonAvatarSubSettings(TypedDict):
    """
    Settings for the avatar button.
    """

    Path: str
    Speak: KeyOptions
    Speak_humor: KeyOptions
    Speak_uncomfortable: KeyOptions


class ShowSettings(TypedDict):
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


class AISettings(TypedDict):
    """
    Settings related to AI behavior and instructions.
    """

    Introduction_instructions: str
    General_instructions: str
    show_watcher_instructions: str
    Avatars: list[AIAvatarSubSettings]  # List of avatar settings


class ModeSettings(TypedDict):
    """
    Settings that control operational modes like Ethics mode and Debug mode.
    """

    Ethic: bool
    Debug: bool


class ButtonSettings(TypedDict):
    """
    Settings related to button configurations.
    """

    Button_debounce_ms: PositiveInt
    Reset: ButtonResetSubSettings
    Avatars: list[ButtonAvatarSubSettings]


class NetworkSettings(TypedDict):
    """
    Settings related to network configurations.
    Not all user will need server certs/keys, but they are included here for completeness.
    """

    Nats_server: str
    Hearing_server: str
    Server_cert_path: str
    Server_key_path: str
    Ca_cert_path: str
    Client_key_path: str
    Client_cert_path: str
    Connection_timeout_s: PositiveInt
    Retry_attempts: PositiveInt
    Retry_backoff_ms: PositiveInt
    Use_tls: bool


class HealthCheckSettings(TypedDict):
    Enabled: bool
    Interval_seconds: int


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

    @model_validator(mode="after")
    def validate_mvp_limits(self):
        # Enforce MVP limitations
        if self.Show["Language"] != "en-US":
            raise ValueError("Only 'en-US' language is supported in MVP.")
        if self.Show["Type"] != "mono-scene":
            raise ValueError("Only 'mono-scene' show type is supported in MVP.")
        if self.Show["Actors_count"] != 1:
            raise ValueError("Only 1 actor is supported in MVP.")
        if self.Show["Avatar_count"] != 1:
            raise ValueError("Only 1 avatar is supported in MVP.")
        return self

    @model_validator(mode="after")
    def validate_avatars_count(self):
        if len(self.Buttons["Avatars"]) != self.Show["Avatar_count"]:
            raise ValueError("Buttons.Avatar count must match Show.Avatar_count.")
        if len(self.AI["Avatars"]) != self.Show["Avatar_count"]:
            raise ValueError("AI.Avatar count must match Show.Avatar_count.")
        return self

    @model_validator(mode="after")
    def validate_ethic_mode(self):
        if self.Mode["Ethic"]:
            if self.Show["Show_rating"] not in ["g", "pg", "pg-13"]:
                raise ValueError("In Ethic mode, Show_rating must be g, pg, or pg-13.")
            if self.Show["Disclaimer"] not in ["short", "full"]:
                raise ValueError("In Ethic mode, Disclaimer must be short or full.")
            if self.Mode["Debug"]:
                raise ValueError(
                    "Ethic mode and Debug mode cannot be enabled simultaneously."
                )
            if self.Network["Use_tls"] is not True:
                raise ValueError("TLS must be enabled in Ethics mode.")
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
