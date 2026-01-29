import importlib
import sys
import tomllib
from typing import Any, Final
import logging

from common.config import NetworkConfig, ModeConfig, get_logging_level


logger = logging.getLogger(__name__)


def main() -> None:
    CONFIG_FILE: Final[str] = "/etc/ai-show/config.toml"

    unverified_config: dict[str, Any]
    network_config: NetworkConfig
    mode_config: ModeConfig

    with open(CONFIG_FILE, mode="rb") as fp:
        unverified_config = tomllib.load(fp)
        network_config = NetworkConfig(**unverified_config.get("Network", {}))
        mode_config = ModeConfig(**unverified_config.get("Mode", {}))

    logging.basicConfig(
        stream=sys.stdout,
        level=get_logging_level(mode_config.debug_level),  # pyright: ignore[reportAttributeAccessIssue]
        format="[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
    )

    logger.info("Starting AI Show Application")
    logger.debug(f"Configuration loaded successfully from {CONFIG_FILE}")
    logger.info(f"Application has been set to the role of {mode_config.role}")  # pyright: ignore[reportAttributeAccessIssue]

    try:
        match mode_config.role:  # pyright: ignore[reportAttributeAccessIssue]
            case "ingest":
                importlib.import_module("ingest").start(
                    network_config, mode_config, unverified_config.get("Ingest", {})
                )
            case "vision":
                raise NotImplementedError("This is not yet implemented")  # TODO: implement
            case "hearing":
                raise NotImplementedError("This is not yet implemented")  # TODO: implement
            case "brain":
                raise NotImplementedError("This is not yet implemented")  # TODO: implement
            case "output":
                raise NotImplementedError("This is not yet implemented")  # TODO: implement
            case "health_check":
                raise NotImplementedError("This is not yet implemented")  # TODO: implement
            case _:
                logger.error(f"Unknown role specified in configuration: {mode_config.role}")  # pyright: ignore[reportAttributeAccessIssue]
                sys.exit(1)
    except Exception as e:
        logger.exception(f"An error occurred while running the application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Unhandled exception in main. Exiting... ERROR: {e}")
        sys.exit(1)
