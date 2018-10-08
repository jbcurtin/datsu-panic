import asyncio
import inspect
import logging
import os

# TODO,
# from signal import signal, SIGTERM, SIGINT

from panic import \
    utils as panic_utils, \
    exceptions as panic_exceptions, \
    router as panic_routers, \
    response as panic_responses, \
    datatypes as panic_datatypes, \
    handlers as panic_handlers

logger = logging.getLogger(__name__)

class Panic:
  def __init__(self, params: panic_datatypes.ServiceParams):
    frame_records = inspect.stack()[1]
    name = inspect.getmodulename(frame_records[1])

    self.name = name
    self.params = panic_datatypes.ServiceParams()

    self.router = panic_routers.RouterAPI(self)
    self.request_handler = panic_handlers.RequestHandler(self)
    self.exception_handler = panic_handlers.ExceptionHandler(self)

  # Decorator
  def exception(self, *exceptions):
    """
    Decorates a function to be registered as a handler for exceptions

    :param \*exceptions: exceptions
    :return: decorated function
    """
    def _wrapper(func):
      for exception in exceptions:
        self.exception_handler.add(exception, func)

      return func

    return _wrapper

