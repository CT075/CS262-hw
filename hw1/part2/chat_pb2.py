# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: chat.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\nchat.proto\"\x1b\n\x0cSessionToken\x12\x0b\n\x03tok\x18\x01 \x01(\x05\"\x04\n\x02Ok\"\x16\n\x04User\x12\x0e\n\x06handle\x18\x01 \x01(\t\"\"\n\x05\x45rror\x12\x0c\n\x04\x63ode\x18\x01 \x01(\x05\x12\x0b\n\x03msg\x18\x02 \x01(\t\"D\n\x03Msg\x12\x0c\n\x04text\x18\x01 \x01(\t\x12\x15\n\x06sender\x18\x02 \x01(\x0b\x32\x05.User\x12\x18\n\trecipient\x18\x03 \x01(\x0b\x32\x05.User\"<\n\x0bSendRequest\x12\x11\n\x03msg\x18\x01 \x01(\x0b\x32\x04.Msg\x12\x1a\n\x03tok\x18\x02 \x01(\x0b\x32\r.SessionToken\"@\n\tOkOrError\x12\x11\n\x02ok\x18\x01 \x01(\x0b\x32\x03.OkH\x00\x12\x15\n\x03\x65rr\x18\x02 \x01(\x0b\x32\x06.ErrorH\x00\x42\t\n\x07payload\"T\n\x13SessionTokenOrError\x12\x1b\n\x02ok\x18\x01 \x01(\x0b\x32\r.SessionTokenH\x00\x12\x15\n\x03\x65rr\x18\x02 \x01(\x0b\x32\x06.ErrorH\x00\x42\t\n\x07payload\" \n\x08UserList\x12\x14\n\x05users\x18\x01 \x03(\x0b\x32\x05.User2\xdf\x01\n\x0b\x43hatSession\x12\x1d\n\x06\x43reate\x12\x05.User\x1a\n.OkOrError\"\x00\x12\x1d\n\tListUsers\x12\x03.Ok\x1a\t.UserList\"\x00\x12\x1a\n\nDeleteUser\x12\x05.User\x1a\x03.Ok\"\x00\x12&\n\x05Login\x12\x05.User\x1a\x14.SessionTokenOrError\"\x00\x12\'\n\x0cIncomingMsgs\x12\r.SessionToken\x1a\x04.Msg\"\x00\x30\x01\x12%\n\x07SendMsg\x12\x0c.SendRequest\x1a\n.OkOrError\"\x00\x62\x06proto3')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'chat_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _SESSIONTOKEN._serialized_start=14
  _SESSIONTOKEN._serialized_end=41
  _OK._serialized_start=43
  _OK._serialized_end=47
  _USER._serialized_start=49
  _USER._serialized_end=71
  _ERROR._serialized_start=73
  _ERROR._serialized_end=107
  _MSG._serialized_start=109
  _MSG._serialized_end=177
  _SENDREQUEST._serialized_start=179
  _SENDREQUEST._serialized_end=239
  _OKORERROR._serialized_start=241
  _OKORERROR._serialized_end=305
  _SESSIONTOKENORERROR._serialized_start=307
  _SESSIONTOKENORERROR._serialized_end=391
  _USERLIST._serialized_start=393
  _USERLIST._serialized_end=425
  _CHATSESSION._serialized_start=428
  _CHATSESSION._serialized_end=651
# @@protoc_insertion_point(module_scope)
