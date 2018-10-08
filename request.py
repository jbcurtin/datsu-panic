import logging
import typing

from collections import namedtuple
from http.cookies import SimpleCookie
from httptools import parse_url
from urllib.parse import parse_qsl, parse_qs
from ujson import loads as json_loads
from panic import \
    datatypes as panic_datatypes, \
    exceptions as panic_exceptions

logger = logging.getLogger(__name__)

DEFAULT_HTTP_CONTENT_TYPE = "application/octet-stream"
# HTTP/1.1: https://www.w3.org/Protocols/rfc2616/rfc2616-sec7.html#sec7.2.1
# > If the media type remains unknown, the recipient SHOULD treat it
# > as type "application/octet-stream"

class RequestParameters(dict):
  """
  Hosts a dict with lists as values where get returns the first
  value of the list and getlist returns the whole shebang
  """

  def __init__(self, params, **kwargs):
    for param, value in params:
      if param in self.keys():
        if isinstance(self[param], list):
          self[param].append(value)

        else:
          self[param] = [self[param], value]

      else:
        self[param] = value
      
  def unwrap(self):
    return {param: value for param, value in self.items()}

  def __repr__(self):
    return f'RequestParameters[len(self.keys())]'

class RequestBody:
  _parts: typing.List[bytes]
  # __slots__ = '_parts',
  def __init__(self) -> None:
    self._parts = []

  def append(self, part: bytes) -> None:
    self._parts.append(part)

  def __repr__(self) -> str:
    return f'RequestBody[{len(self._parts)}]'

  @property
  def extract(self) -> bytes:
    return b''.join(self._parts)

class Request(dict):
  url: str
  headers: panic_datatypes.HTTPHeaders
  version: str
  method: panic_datatypes.HTTPMethod
  query_string: str
  body: RequestBody
  _parsed: typing.Dict[str, typing.Any]
  _encoding: str

  # __slots__ = (
  #   'url', 'headers', 'version', 'method', '_cookies',
  #   'query_string', 'body',
  #   'parsed_json', 'parsed_args', 'parsed_form', 'parsed_files',
  # )

  def __repr__(self):
    return 'Request[%s]' % self.headers['content-type']

  def __init__(self,
    url: bytes,
    headers: panic_datatypes.HTTPHeaders,
    version: str,
    method: panic_datatypes.HTTPMethod):

    # Assume UTF-8 for all communications.
    self._encoding = 'utf-8'
    parsed_url = parse_url(url)
    self.url = parsed_url.path.decode('utf-8')
    self.query_string = None
    if parsed_url.query:
      self.query_string = parsed_url.query.decode('utf-8')

    self.headers = headers
    self.version = version
    self.method = method
    self.body = RequestBody()
    self._parsed = {}

  @property
  def json(self):
    if not self.headers['content-type'] in ['application/json']:
      raise panic_exceptions.ServerError(f'Content-Type[{self.headers["content-type"].value}] not supported')

    if not 'json' in self._parsed.keys():
      try:
        self._parsed['json'] = json_loads(self.body.extract.decode(self._encoding))

      except ValueError as err:
        raise panic_exceptions.BadRequest(f'Unable to decode request-body of Content-Type[{self.headers["content-type"].value}]')

      except Exception as err:
        print(err)
        import ipdb;ipdb.set_trace()
        raise err

    return self._parsed['json']

  @property
  def form(self):
    if not self.headers['content-type'] in ['application/x-www-form-urlencoded', 'multipart/form-data', DEFAULT_HTTP_CONTENT_TYPE]:
      raise panic_exceptions.ServerError(f'Content-Type[{self.headers["content-type"].value}] not supported')

    if not 'form' in self._parsed.keys():
      if self.headers['content-type'] in ['application/x-www-form-urlencoded']:
        self._parsed['form'] = {}
        for name, value in parse_qsl(''.join(self.body.extract.decode(self._encoding))):
          try:
            if not isinstance(self._parsed['form'][name], list):
              self._parsed['form'][name] = [self._parsed['form'][name]]

            self._parsed['form'][name].append(value)
          except KeyError as err:
            logger.debug(err)
            self._parsed['form'][name] = value

      elif self.headers['content-type'] in ['multipart/form-data']:
        File = namedtuple('File', ['content_type', 'body', 'parameters'])
        self._parsed['form'] = {'files': []}
        for part in self.body.extract.split(self.headers['content-type'].parameters['boundary'].encode(self._encoding))[1:-1]:
          headers, body = part.split(b'\r\n\r\n')
          headers = panic_datatypes.HTTPHeaders().parse([header for header in headers.decode(self._encoding).split('\r\n') if header])
          body = body.strip(b'\r\n--')
          try:
            content_type = headers['content-type'].value
          except AttributeError as err:
            content_type = None
            pass

          try:
            parameters = headers['content-disposition'].parameters
          except AttributeError as err:
            parameters = None
            pass

          self._parsed['form']['files'].append(File(content_type, body, parameters))

      else:
        import ipdb; ipdb.set_trace()
        raise NotImplementedError

    return self._parsed['form']

  @property
  def cookies(self):
    raise NotImplementedError

  @property
  def query(self):
    if not 'query' in self._parsed.keys():
      self._parsed['query'] = RequestParameters(parse_qsl(self.query_string))

    return self._parsed['query']

