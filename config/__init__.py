import os
import tomli  # Use tomllib for Python 3.11 and later


class Config:
    def __init__(self):
        config_file = os.path.join(os.path.dirname(__file__), 'config.toml')
        with open(config_file, 'rb') as file:
            self.config = tomli.load(file)

    def get(self, *keys, default=None):
        # Join keys to create an env var name, e.g., APP_NAME
        env_key = '_'.join(keys).upper()
        env_value = os.getenv(env_key)

        # Return the environment variable if it exists
        if env_value is not None:
            return env_value

        # Otherwise, get from TOML
        data = self.config
        for key in keys:
            data = data.get(key, default)
            if data is None:
                break
        return data


config = Config()
