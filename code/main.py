import importlib
import sys
from typing import Final
import logging

import config as cfg

logger = logging.getLogger(__name__)


def main() -> None:
    # CONFIG_FILE: Final[str] = "testing/good_config.toml"
    CONFIG_FILE: Final[str] = "/etc/ai-show/config.toml"

    config: cfg.Config
    try:
        config = cfg.generate_config(CONFIG_FILE)
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        sys.exit(1)

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.DEBUG if config.Mode.Debug else logging.INFO,
        format="[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
    )

    logger.info("Starting AI Show Application")
    logger.debug(f"Configuration loaded successfully from {CONFIG_FILE}")
    logger.info(f"Application has been set to the role of {config.Mode.Role}")

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


if __name__ == "__main__":
    main()
