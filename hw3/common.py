from typing import NewType

Host = NewType("Host", str)
Port = NewType("Port", int)


class Ok:
    def to_jsonable_type(self):
        return "ok"


User = NewType("User", str)
