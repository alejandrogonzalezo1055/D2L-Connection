from functools import lru_cache


class LPService():
    def __init__(self):
        self.lp_version = 1.64

    def whoami(self):
        ...


@lru_cache()
def get_service() -> LPService:
    return LPService()