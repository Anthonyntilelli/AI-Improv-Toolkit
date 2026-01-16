from config import Config, generate_config

CONFIG_FILE = "testing/good_config.toml"


def main() -> None:
    config: Config = generate_config(CONFIG_FILE)
    print("Configuration successfully validated and loaded.")
    print(config)


if __name__ == "__main__":
    main()
