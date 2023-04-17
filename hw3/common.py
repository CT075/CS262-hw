from typing import NewType, Tuple

Host = NewType("Host", str)
Port = NewType("Port", int)
Address = Tuple[Host, Port]


class Ok:
    def to_jsonable_type(self):
        return "ok"


User = NewType("User", str)
