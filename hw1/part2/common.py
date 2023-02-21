from chat_pb2 import Error

# We can't inherit from [Error] directly because protobuf sucks
class UserError(Exception):
    code: int
    msg: str

    def __init__(self, *, code, msg):
        self.code = code
        self.msg = msg

    def into(self) -> Error:
        return Error(code=self.code, msg=self.msg)
