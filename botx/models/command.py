from typing import Callable


class Command:
    names: list[str]

    func: Callable

    private: bool
    group: bool
    admin: bool

    def __init__(
        self,
        names: list[str],
        func: Callable,
        private: bool = False,
        group: bool = False,
        admin: bool = False,
    ):
        self.names = names
        self.func = func
        self.private = private
        self.group = group
        self.admin = admin
