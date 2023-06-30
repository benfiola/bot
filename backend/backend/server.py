from fastapi import FastAPI

from backend.configuration import Configuration

class Server(FastAPI):
    _configuration: Configuration | None

    def __init__(self):
        self._configuration = None

    def configure(self, configuration: Configuration):
        self._configuration = configuration

    def get_configuration(self) -> Configuration:
        if not self._configuration:
            raise RuntimeError(f"server is not configured")
        return self._configuration

    def run(self):
        pass
    