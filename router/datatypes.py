import hashlib
import inspect
import typing

from urllib.parse import urlparse

from panic import datatypes as panic_datatypes

PWN = typing.TypeVar('PWN')
class URIRoute:
  url: str
  handler: panic_datatypes.FunctionType
  method: panic_datatypes.HTTPMethod
  awaitable: bool

  @property
  def identity(self):
    return self.__hash__()

  @staticmethod
  def route_hasher(typed_url: str, method: panic_datatypes.HTTPMethod) -> str:
    return hashlib.md5(':'.join([
      typed_url,
      method.name.lower(),
    ]).encode('utf-8')).hexdigest()

  def __init__(self,
      url: str,
      method: panic_datatypes.HTTPMethod,
      handler: panic_datatypes.FunctionType,
      awaitable: bool = False,
      streamable: bool = False,
      socket_encoding: str = 'application/octet-stream',
      socket_protocol: str = 'topics') -> None:
    self.url = url
    self.handler = handler
    self.method = method
    self.awaitable = awaitable
    # https://docs.python.org/3.6/library/inspect.html#inspect.isasyncgenfunction
    self.streamable = streamable
    # https://tools.ietf.org/html/rfc6455#page-12
    self.socket_encoding = socket_encoding
    self.socket_protocol = socket_protocol

  def __hash__(self) -> int:
    return hash(URIRoute.route_hasher(self.url, self.method))

  def __eq__(self, other: PWN) -> bool:
    return self.__hash__() == other.__hash__()

  def __repr__(self) -> str:
    return f'URIRoute[{self.method.name}:{self.url}]'

