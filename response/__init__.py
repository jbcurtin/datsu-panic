import typing

import json as pjson

from panic import \
    exceptions as panic_exceptions, \
    datatypes as panic_datatypes
from panic.response import \
    datatypes as response_datatypes

KEEP_ALIVE = 5
class Response:
  __slots__ = ('body', 'status', 'headers', 'cookies')
  def __init__(self, body: bytes = None, status: int = 200, headers: typing.Dict = {}, cookies: typing.Dict = {}) -> None:
    self.headers = panic_datatypes.HTTPHeaders().merge(headers)
    if 'content-type' not in self.headers:
      raise panic_exceptions.MissingRequiredHeader('Content-Type')

    if 'keep-alive' not in self.headers:
      self.headers.append('connection', 'keep-alive')
      self.headers.append('keep-alive', f'timeout={KEEP_ALIVE}')

    self.headers.append('content-length', str(len(body)))

    self.cookies = panic_datatypes.HTTPCookies().merge(cookies)
    self.body = body
    self.status = status

  def assimilate(self, name: str, value) -> None:
    self.headers.append(name, value)

  def channel(self, version: str = '1.1') -> typing.Any:
    return b'\r\n'.join([
      f'HTTP/{version} 101 Switching Protocols'.encode(),
      self.headers.render(),
      #self.cookies.render(),
      b'',
      b''])

  def output(self, version: str = '1.1') -> bytes:
    return b'\r\n'.join([
      f'HTTP/{version} {self.status:d}'.encode(),
      self.headers.render(),
      #self.cookies.render(),
      b'',
      self.body
    ])

  def __repr__(self):
    return 'Response[%s:%s]' % (self.headers['content-length'], self.headers['content-type'])

  # @property
  # https://tools.ietf.org/html/rfc6265#section-3.1
  # def cookies(self):
  #   if self._cookies is None:
  #     self._cookies = CookieJar(self.headers)

  #  return self._cookies

def json_dumps(datum: typing.Dict[typing.Any, typing.Any]) -> str:
  # ujson
  return pjson.dumps(datum)

def json(body: typing.Dict, status: int = 200, headers: typing.Dict[str, str] = {}) -> Response:
  headers['Content-Type'] = 'application/json'
  return Response(json_dumps(body).encode('utf-8'), status=status, headers=headers)

def text(body: str, status: int = 200, headers: typing.Dict[str, str] = {}) -> Response:
  headers['Content-Type'] = 'text/plain'
  return Response(body.encode('utf-8'), status=status, headers=headers)

# async def file(location, mime_type=None, headers=None):
#     filename = path.split(location)[-1]
# 
#     async with open_async(location, mode='rb') as _file:
#         out_stream = await _file.read()
# 
#     mime_type = mime_type or guess_type(filename)[0] or 'text/plain'
# 
#     return HTTPResponse(status=200,
#                         headers=headers,
#                         content_type=mime_type,
#                         body_bytes=out_stream)
