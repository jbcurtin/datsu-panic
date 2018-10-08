import asyncio
import cgi
import enum
import hashlib
import logging
import os
import typing

from panic import exceptions as panic_exceptions

logger = logging.getLogger(__name__)

ExceptionType = Exception
FunctionType = (lambda: None).__class__
PWN = typing.TypeVar('PWN')

class HTTPHeader:
  name: str
  value: str
  _parameters: typing.Dict[str, typing.Any]
  __slots__ = ('name', 'value', '_parameters')

  def __init__(self, name: str, value: str) -> None:
    self.name = name.lower() # axios
    self.value = value

  def __hash__(self):
    return hash(self.value.split(';', 1)[0])

  def __eq__(self, other: PWN) -> bool:
    return self.__hash__() == other.__hash__()

  def __repr__(self):
    return f'HTTPHeader[{self.name, self.value}]'

  def encode(self, encoding='utf-8') -> bytes:
    return b':'.join([
      self.name.encode(encoding),
      self.value.encode(encoding)])

  @property
  def parameters(self) -> typing.Dict[str, typing.Any]:
    if hasattr(self, '_parameters'):
      return self._parameters

    self._parameters = cgi.parse_header(self.value)[1]
    return self._parameters

class HTTPMethod(enum.Enum):
  joint: str = 'joint'
  get: str = 'get'
  post: str = 'post'
  put: str = 'put'
  channel: str = 'channel'

  @classmethod
  def Match(cls: type, name: str) -> PWN:
    for item in cls:
      if item.name.lower() == name.lower():
        return item

    raise panic_exceptions.InvalidHTTPMethod(name)

class HTTPCookies:
  _cookies: typing.Dict
  __slots__ = ('_cookies',)

  def __init__(self) -> None:
    self._cookies = {}

  def merge(self, datum: typing.Dict[str, str], as_defaults: bool = False) -> PWN:
    logger.warn('NotImplemented')
    return self

class HTTPHeaders:
  _headers: typing.Dict[str, HTTPHeader]
  __slots__ = ('_headers',)

  def __contains__(self, item: str) -> bool:
    return item in self._headers.keys()

  def __init__(self) -> None:
    self._headers = {}
    self.append('Content-Type', 'text/plain')

  def append(self, name: str, value: str) -> HTTPHeader:
    self._headers[name.lower()] = HTTPHeader(name, value)
    return self._headers[name.lower()]

  def __setitem__(self, name: str, value: HTTPHeader) -> None:
    self._headers[name.lower()] = value

  def __getitem__(self, name: str) -> HTTPHeader:
    try:
      return self._headers[name.lower()]
    except KeyError as err:
      raise KeyError(f'Header[{name}] not fould')

  def get(self, name: str) -> str:
    try:
      return self[name]
    except KeyError as err:
      logger.debug(err)

    return None

  def keys(self):
    return self._headers.keys()

  def parse(self, datum_list: typing.List[str], as_defaults: bool = False) -> PWN:
    for datum in datum_list:
      self.append(*datum.split(':'))

    return self

  def merge(self, datum: typing.Dict[str, str], as_defaults: bool = False) -> PWN:
    if not as_defaults:
      for name, value in datum.items():
        self.append(name, value)
    else:
      # This isn't working for some reason...
      import pytest; pytest.set_trace()
      for name, value in datum.items():
        if name in datum.keys():
          logger.debug(f'skipping {name}')
        else:
          self.append(name, value)

    return self

  def render(self) -> bytes:
    return b'\r\n'.join(value.encode() for value in self._headers.values())

  def __repr__(self):
    return f'HTTPHeaders[{len(self._headers)}]'

class ServiceParams:
  supported_methods: typing.List[HTTPMethod] = list(HTTPMethod)
  debug: bool = os.environ.get('WWW_DEBUG', None)

class Signal():
  def __init__(self) -> None:
    self.stopped = False

class ServerParams:
  host: str = os.environ.get('WWW_HOST', None)
  port: int = int(os.environ.get('WWW_PORT', None))
  sock: object = None
  debug: bool = os.environ.get('WWW_DEBUG', None)
  loop: object = None
  request_timeout: int = int(os.environ.get('WWW_REQUEST_TIMEOUT', 15))
  signal: object = Signal()
  connections: set = set()
  reuse_port: bool = False
  protocol: asyncio.Protocol = None
  request_handler: object
  error_handler: object

#service_settings = SERVICE_APP._helper(loop=EVENT_LOOP,
#    host=WWW_HOST, port=WWW_PORT, debug=WWW_DEBUG, ssl=None, sock=None,
#    workers=WWW_WORKERS, protocol=HttpProtocol, backlog=100,
#    register_sys_signals=True, run_async=False, access_log=True)

