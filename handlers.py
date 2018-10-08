import asyncio
import hashlib
import inspect
import logging
import os
import traceback
import typing

from panic import \
    request as panic_request, \
    response as panic_response, \
    datatypes as panic_datatypes, \
    exceptions as panic_exceptions

WWW_DEBUG = False if os.environ.get('WWW_DEBUG', 't') == 'f' else True
logger = logging.getLogger(__name__)

class RequestHandler:
  _panic: object
  def __init__(self, panic_service):
    self._panic = panic_service

  async def __call__(self,
      request: panic_request.Request,
      response_callback: typing.Any,
      transport: asyncio.BaseTransport = None) -> typing.Any:

    try:
      uri_route = self._panic.router.request(request.method, request.url)
    except panic_exceptions.NotFound as err:
      if WWW_DEBUG:
        response = panic_response.text(f'Method[{request.method}] and Route[{request.url}] does not exist', status=500)

      else:
        response = panic_response.text('Service Error', status=500)

      response_callback(response)
      return None

    if uri_route.streamable:
      raise NotImplementedError

    if uri_route.method is panic_datatypes.HTTPMethod.channel:
      while True:
        response = await uri_route.handler(request, response_callback)
        if response in [0]:
          break

      await response_callback.close()
      transport.close()

    elif uri_route.awaitable:
      try:
        response = await uri_route.handler(request)
      except Exception as err:
        try:
          if inspect.iscoroutinefunction(self._panic.exception_handler):
            response = self._panic.exception_handler(request, err)
          else:
            response = self._panic.exception_handler(request, err)
        except Exception as errZero:
          if self._panic.params.debug:
            response = panic_response.text(f'Error[{errZero}] while handling error[{err}]', status=500)
          else:
            response = panic_response.text('Internal Error', status=500)

      response_callback(response)
    else:
      raise NotImplementedError

class ExceptionHandler:
  _panic: object
  handlers: typing.Dict[panic_datatypes.ExceptionType, panic_datatypes.FunctionType]
  def __init__(self, panic_service):
    self.handlers = {}
    self._panic = panic_service

  def add(self, exception: panic_datatypes.ExceptionType, handler: panic_datatypes.FunctionType) -> None:
    if exception is self.handlers.keys():
      raise panic_exceptions.InvalidAttribute(f'exception[{exception}] is already registered')

    self.handlers[exception] = handler

  def __call__(self, request: panic_request.Request, exception: Exception) -> panic_response.Response:
    if self._panic.params.debug:
      logger.exception(exception)

    for key, handler in self.handlers.items():
      if issubclass(type(exception), key):
        return handler(request=request, exception=exception)

    return self._default(request=request, exception=exception)

  def _default(self, request: panic_request.Request, exception: panic_datatypes.ExceptionType) -> panic_response.Response:
    if issubclass(type(exception), panic_exceptions.PanicException):
      return panic_response.text(f'Error: {exception}', status=getattr(exception, 'status', 500))

    elif self._panic.params.debug:
      return panic_response.text(f'Error: {exception}\nException: {traceback.format_exc()}', status=500)

    return panic_response.text("An error occurred that Panic couldn't handle correctly.", status=500)

