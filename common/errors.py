from fastapi import FastAPI
from functools import lru_cache
import logging


# Formato: [Fecha y hora] [Nivel] [Nombre del Logger - Archivo:Línea] - Mensaje
formato = logging.Formatter(
    fmt="[%(asctime)s] [%(levelname)s] [%(name)s - %(filename)s:%(lineno)d]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

class Logger():
    def __init__(self):
        self.logger = logging.getLogger("D2L-Connection Logger")
        self.logger.setLevel(logging.DEBUG)
        self.handler = logging.StreamHandler()
        self.handler.setFormatter(formato)
        self.logger.addHandler(self.handler)


@lru_cache()
def get_logger() -> Logger:
    return Logger()


def register_error_handler(app: FastAPI) -> None:
    ...