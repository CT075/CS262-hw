# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import chat_pb2 as chat__pb2


class ChatSessionStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Create = channel.unary_unary(
                '/ChatSession/Create',
                request_serializer=chat__pb2.User.SerializeToString,
                response_deserializer=chat__pb2.OkOrError.FromString,
                )
        self.ListUsers = channel.unary_unary(
                '/ChatSession/ListUsers',
                request_serializer=chat__pb2.Ok.SerializeToString,
                response_deserializer=chat__pb2.UserList.FromString,
                )
        self.DeleteUser = channel.unary_unary(
                '/ChatSession/DeleteUser',
                request_serializer=chat__pb2.User.SerializeToString,
                response_deserializer=chat__pb2.Ok.FromString,
                )
        self.Login = channel.unary_unary(
                '/ChatSession/Login',
                request_serializer=chat__pb2.User.SerializeToString,
                response_deserializer=chat__pb2.SessionTokenOrError.FromString,
                )
        self.IncomingMsgs = channel.unary_stream(
                '/ChatSession/IncomingMsgs',
                request_serializer=chat__pb2.SessionToken.SerializeToString,
                response_deserializer=chat__pb2.Msg.FromString,
                )
        self.SendMsg = channel.unary_unary(
                '/ChatSession/SendMsg',
                request_serializer=chat__pb2.SendRequest.SerializeToString,
                response_deserializer=chat__pb2.OkOrError.FromString,
                )


class ChatSessionServicer(object):
    """Missing associated documentation comment in .proto file."""

    def Create(self, request, context):
        """See [README.md] for a high-level description of these endpoints.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def ListUsers(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def DeleteUser(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Login(self, request, context):
        """GRPC doesn't allow for the same kind of session management as our
        homegrown [jsonrpc] infra, so we need to have some restrictions.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def IncomingMsgs(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def SendMsg(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_ChatSessionServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'Create': grpc.unary_unary_rpc_method_handler(
                    servicer.Create,
                    request_deserializer=chat__pb2.User.FromString,
                    response_serializer=chat__pb2.OkOrError.SerializeToString,
            ),
            'ListUsers': grpc.unary_unary_rpc_method_handler(
                    servicer.ListUsers,
                    request_deserializer=chat__pb2.Ok.FromString,
                    response_serializer=chat__pb2.UserList.SerializeToString,
            ),
            'DeleteUser': grpc.unary_unary_rpc_method_handler(
                    servicer.DeleteUser,
                    request_deserializer=chat__pb2.User.FromString,
                    response_serializer=chat__pb2.Ok.SerializeToString,
            ),
            'Login': grpc.unary_unary_rpc_method_handler(
                    servicer.Login,
                    request_deserializer=chat__pb2.User.FromString,
                    response_serializer=chat__pb2.SessionTokenOrError.SerializeToString,
            ),
            'IncomingMsgs': grpc.unary_stream_rpc_method_handler(
                    servicer.IncomingMsgs,
                    request_deserializer=chat__pb2.SessionToken.FromString,
                    response_serializer=chat__pb2.Msg.SerializeToString,
            ),
            'SendMsg': grpc.unary_unary_rpc_method_handler(
                    servicer.SendMsg,
                    request_deserializer=chat__pb2.SendRequest.FromString,
                    response_serializer=chat__pb2.OkOrError.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'ChatSession', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class ChatSession(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def Create(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/ChatSession/Create',
            chat__pb2.User.SerializeToString,
            chat__pb2.OkOrError.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def ListUsers(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/ChatSession/ListUsers',
            chat__pb2.Ok.SerializeToString,
            chat__pb2.UserList.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def DeleteUser(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/ChatSession/DeleteUser',
            chat__pb2.User.SerializeToString,
            chat__pb2.Ok.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def Login(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/ChatSession/Login',
            chat__pb2.User.SerializeToString,
            chat__pb2.SessionTokenOrError.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def IncomingMsgs(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_stream(request, target, '/ChatSession/IncomingMsgs',
            chat__pb2.SessionToken.SerializeToString,
            chat__pb2.Msg.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def SendMsg(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/ChatSession/SendMsg',
            chat__pb2.SendRequest.SerializeToString,
            chat__pb2.OkOrError.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
