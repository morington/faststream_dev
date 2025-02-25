from typing import NewType

from dishka import provide, Provider, Scope

# t_config = NewType("t_config", dict)

class ConfigProvider(Provider):
    scope = Scope.APP

    @provide
    def get_config(self) -> dict:
        return dict()
