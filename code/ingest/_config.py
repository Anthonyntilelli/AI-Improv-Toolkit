"""
Will validate the internal.toml configuration file.
"""
from pathlib import Path
import tomllib
from typing import Final, Literal, Any


from pydantic import BaseModel, ConfigDict, PositiveInt




INTERNAL_CONFIG_PATH: Final[str] = f"{Path(__file__).resolve().parent / 'internal.toml'}"


class _AudioSettings(BaseModel):
    """
    Audio settings configuration. Channels is not part of the internal.toml file,
    it need to be derived from the main configuration file, at from config.Show["Actors_count"].
    """

    model_config = ConfigDict(extra="forbid")
    Sample_rate: PositiveInt
    Channels: Literal[1, 2]
    Pre_roll_ms: PositiveInt
    Post_roll_ms: PositiveInt
    Chunk_size_ms: PositiveInt
    Vad_aggressiveness: Literal[0, 1, 2, 3]
    Vad_frame_ms: Literal[10, 20, 30]
    Button_debounce_ms: PositiveInt


def _load_internal_config(actorCount: PositiveInt) -> _AudioSettings:
    """
    Generates a AudioSettings object from a TOML configuration file.
    Any raised validation errors will be propagated to the caller.

    :param actorCount: Number of actors derived from the main configuration file
    :type actorCount: PositiveInt
    :return: Valid AudioSettings object for the AI Improv Toolkit
    :rtype: AudioSettings
    """

    unverified_internal_config: dict[str, Any]

    with open(INTERNAL_CONFIG_PATH, mode="rb") as fp:
        unverified_internal_config = tomllib.load(fp)

    unverified_internal_config["Channels"] = actorCount
    print(unverified_internal_config)
    return _AudioSettings(**unverified_internal_config)
