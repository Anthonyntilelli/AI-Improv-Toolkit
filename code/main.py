import importlib
import sys
from typing import Final
import logging

import common.config as cfg

logger = logging.getLogger(__name__)

# TODO: Before merge: Set up reset action.


def main() -> None:
    # CONFIG_FILE: Final[str] = "testing/good_config.toml"
    CONFIG_FILE: Final[str] = "/etc/ai-show/config.toml"

    config: cfg.Config
    try:
        config = cfg.generate_config(CONFIG_FILE)
    except Exception as e:
        print(f"Failed to load {CONFIG_FILE} configuration: {e}", file=sys.stderr)
        sys.exit(1)

    logging.basicConfig(
        stream=sys.stdout,
        level=cfg.get_logging_level(config),
        format="[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
    )

    logger.info("Starting AI Show Application")
    logger.debug(f"Configuration loaded successfully from {CONFIG_FILE}")
    logger.info(f"Application has been set to the role of {config.Mode.Role}")
    try:
        match config.Mode.Role:
            case "ingest":
                importlib.import_module("ingest").start(config)
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
                logger.error(f"Unknown role specified in configuration: {config.Mode.Role}")
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
