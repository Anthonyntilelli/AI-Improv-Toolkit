"""
Creates the ingestion configuration model and loads the internal.toml file and general config.
Ingests general configuration from config.Config to create IngestSettings.
All setting needed for ingestion are defined here.
"""

import os
from pathlib import Path
import tomllib
from typing import Final, Literal, Any, NamedTuple, Optional

from pydantic import BaseModel, PositiveInt, model_validator
from common import config as cfg

from common import KeyOptions as KO

INTERNAL_CONFIG_PATH: Final[str] = (
    f"{Path(__file__).resolve().parent / 'internal.toml'}"
)


class ShowSubSettings(NamedTuple):
    """
    Show settings configuration.
    """

    Avatar_count: PositiveInt


class AudioSubSettings(NamedTuple):
    """
    Audio settings configuration. Channels is not part of the internal.toml file,
    it need to be derived from the main configuration file, at from config.Show["Actors_count"].
    """

    Sample_rate: PositiveInt
    Channels: PositiveInt
    Pre_roll_ms: PositiveInt
    Post_roll_ms: PositiveInt
    Chunk_size_ms: PositiveInt
    Vad_aggressiveness: Literal[0, 1, 2, 3]
    Vad_frame_ms: Literal[10, 20, 30]


class Button(NamedTuple):
    """Represents a button configuration."""

    device_path: str
    key: dict[KO, cfg.AllowedActions]  # key with action name
    grab: bool


class ButtonSubSettings(NamedTuple):
    """Settings for all buttons."""

    buttons: list[Button]
    Debounce_ms: PositiveInt


class NetworkSubSettings(NamedTuple):
    """
    Network settings configuration.
    """

    Nats_server: str
    Hearing_server: str
    Connection_timeout_s: PositiveInt
    Retry_attempts: PositiveInt
    Retry_backoff_ms: PositiveInt
    Use_tls: bool
    Ca_cert_path: Optional[str] = None
    Client_cert_path: Optional[str] = None
    Client_key_path: Optional[str] = None


class HealthCheckSubSettings(NamedTuple):
    Enabled: bool
    Interval_seconds: PositiveInt


class IngestSettings(BaseModel):
    """
    Audio settings configuration. Channels is not part of the internal.toml file,
    it need to be derived from the main configuration file, at from config.Show["Actors_count"].
    """

    Show: ShowSubSettings
    Audio: AudioSubSettings
    Buttons: ButtonSubSettings
    Network: NetworkSubSettings
    HealthCheck: HealthCheckSubSettings
    Ethics_mode: bool
    skip_button_validation: bool = False
    ActorMics: list[cfg.MicsSubSettings]

    @model_validator(mode="after")
    def validate_ethics_mode(self):
        if self.Ethics_mode and not self.Network.Use_tls:
            raise ValueError(
                "Ethics mode requires TLS to be enabled in network settings."
            )
        return self

    @model_validator(mode="after")
    def validate_network_settings(self):
        if self.Network.Use_tls:
            for file in [
                self.Network.Ca_cert_path,
                self.Network.Client_cert_path,
                self.Network.Client_key_path,
            ]:
                if file is None:
                    raise ValueError(
                        "TLS is enabled, but file paths are not all provided."
                    )
                if not (Path(file).is_file() and os.access(file, os.R_OK)):
                    raise ValueError(
                        f"TLS is enabled, but certificate/key file {file} is not accessible."
                    )
        return self

    @model_validator(mode="after")
    def validate_buttons(self):
        if self.skip_button_validation:
            return self
        for button in self.Buttons.buttons:
            p = Path(button.device_path)
            if not p.exists():
                raise ValueError(f"Button device path {p} does not exist.")
            if not p.is_char_device():
                raise ValueError(f"Button device path {p} is not a character device.")

            flags = (
                os.O_RDONLY | os.O_NONBLOCK
            )  # Open in non-blocking read-only mode (to avoid blocking if grabbed)
            try:
                fd = os.open(button.device_path, flags)
                os.close(fd)
            except OSError as e:
                raise ValueError(
                    f"Button device path {button.device_path} is not accessible: {e}"
                ) from e
        return self

    @model_validator(mode="after")
    def validate_audio_device(self):
        actor_mics = self.ActorMics
        for mic in actor_mics:
            audio_device = Path(mic.Mic_path)
            if not audio_device.exists():
                raise ValueError(
                    f"Audio capture device path {audio_device} does not exist."
                )
            if not audio_device.is_char_device():
                raise ValueError(
                    f"Audio capture device path {audio_device} is not a character device, likely not an audio device."
                )

            # Open in non-blocking read-only mode (to avoid blocking if grabbed)
            flags = os.O_RDONLY | os.O_NONBLOCK
            try:
                fd = os.open(audio_device, flags)
                os.close(fd)
            except OSError as e:
                raise ValueError(
                    f"Audio capture device path {audio_device} is not accessible: {e}"
                ) from e
        return self

    # TODO Enable audio validation when needed
    # @model_validator(mode="after")
    # def validate_audio(self):
    #     if self.Audio.Pre_roll_ms + self.Audio.Post_roll_ms < self.Audio.Chunk_size_ms:
    #         raise ValueError("Pre_roll_ms + Post_roll_ms must be at least Chunk_size_ms.")
    #     if self.Audio.Pre_roll_ms < self.Audio.Chunk_size_ms:
    #         raise ValueError("Pre_roll_ms must be at least Chunk_size_ms.")
    #     return self


def load_internal_config(
    config: cfg.Config, skip_button_validation: bool = False
) -> IngestSettings:
    """
    Load and validate the internal.toml configuration file.
    """

    unverified_internal_config: dict[str, Any]

    with open(INTERNAL_CONFIG_PATH, mode="rb") as fp:
        try:
            unverified_internal_config = tomllib.load(fp)
        except Exception as e:
            raise RuntimeError(
                f"Failed to load internal configuration from {INTERNAL_CONFIG_PATH}: {e}"
            ) from e

    reset_button: Button = Button(
        device_path=config.Buttons.Reset.Path,
        key={config.Buttons.Reset.Key: "reset"},
        grab=config.Buttons.Reset.grab,
    )

    avatar_buttons: list[Button] = []
    for btn in config.Buttons.Avatars:
        avatar_buttons.append(
            Button(device_path=btn.Path, key={btn.Speak: "speak"}, grab=btn.grab)
        )

    # Derive settings from the main config
    setting: IngestSettings = IngestSettings(
        Show=ShowSubSettings(Avatar_count=config.Show.Avatar_count),
        Audio=AudioSubSettings(
            **unverified_internal_config["Audio"], Channels=config.Show.Actors_count
        ),
        Buttons=ButtonSubSettings(
            buttons=[reset_button] + avatar_buttons,
            Debounce_ms=unverified_internal_config["Button"]["Debounce_ms"],
        ),
        Network=NetworkSubSettings(
            Client_cert_path=unverified_internal_config["Network"]["Client_cert_path"],
            Client_key_path=unverified_internal_config["Network"]["Client_key_path"],
            Nats_server=config.Network.Nats_server,
            Hearing_server=config.Network.Hearing_server,
            Ca_cert_path=config.Network.Ca_cert_path,
            Connection_timeout_s=config.Network.Connection_timeout_s,
            Retry_attempts=config.Network.Retry_attempts,
            Retry_backoff_ms=config.Network.Retry_backoff_ms,
            Use_tls=config.Network.Use_tls,
        ),
        HealthCheck=HealthCheckSubSettings(
            Enabled=config.Health_Check.Enabled,
            Interval_seconds=config.Health_Check.Interval_seconds,
        ),
        Ethics_mode=config.Mode.Ethic,
        skip_button_validation=skip_button_validation,
        ActorMics=config.Actors.Mics,
    )

    return setting
