import importlib
import sys
import tomllib
from typing import Any, Final
import logging

from common.config import ModeConfig, ShowConfig, get_logging_level, WebrtcConfig


logger = logging.getLogger(__name__)


def main() -> None:
    CONFIG_FILE: Final[str] = "/etc/ai-show/config.toml"
    # CONFIG_FILE: Final[str] = "./config/config.toml"


    unverified_config: dict[str, Any]
    mode_config: ModeConfig
    webrtc_config: WebrtcConfig

    with open(CONFIG_FILE, mode="rb") as fp:
        unverified_config = tomllib.load(fp)
        show_config = ShowConfig(**unverified_config.get("Show", {}))
        mode_config = ModeConfig(**unverified_config.get("Mode", {}))
        webrtc_config = WebrtcConfig(**unverified_config.get("Webrtc", {}))



    logging.basicConfig(
        stream=sys.stdout,
        level=get_logging_level(mode_config.debug_level),
        format="[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
    )

    logger.info("Starting AI Show Application")
    logger.debug(f"Configuration loaded successfully from {CONFIG_FILE}")
    logger.info(f"Application has been set to the role of {mode_config.role}")

    try:
        match mode_config.role:
            case "frontend":
                importlib.import_module("frontend").start(
                    show_config, webrtc_config, mode_config, unverified_config.get("Frontend", {})
                )
            case "backend":
                raise NotImplementedError("This is not yet implemented")  # TODO: implement
            case _:
                logger.error(f"Unknown role specified in configuration: {mode_config.role}")
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
