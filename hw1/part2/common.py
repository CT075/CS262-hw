from chat_pb2 import Error


class UserError(Error, Exception):
    def __init__(self, *, code, message):
        Error.__init__(self, code=code, msg=message)
