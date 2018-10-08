import asyncio
import datetime
import logging
import uuid

from pprint import pprint
from httptools import HttpRequestParser, HttpParserUpgrade
from httptools.parser.errors import HttpParserError

from panic import \
    datatypes as panic_datatypes, \
    utils as panic_utils, \
    exceptions as panic_exceptions, \
    request as panic_request, \
    response as panic_response

from websockets import WebSocketCommonProtocol, InvalidHandshake, handshake

logger = logging.getLogger(__name__)

class WebSocketProtocol(asyncio.Protocol):
  def __init__(self, params: panic_datatypes.ServerParams):
    self.enabled = False
    self.params = params
    self.websocket = None
    self.transport = None
    self.timeout = params.request_timeout or 10
    self.max_size = 2 ** 20
    self.max_queue = 2 ** 5
    self.read_limit =  2 ** 16
    self.write_limit = 2 ** 16

    self.url = None
    self.connections = params.connections

    self.request = None
    self.headers = panic_datatypes.HTTPHeaders()
    self.parser = HttpRequestParser(self)

    self._last_request_time = None

    self._identity = uuid.uuid4()


  def connection_made(self, transport):
    self.connections.add(self)
    self._timeout_handler = self.params.loop.call_later(self.timeout, self.connection_timeout)
    self.transport = transport
    self._last_request_time = datetime.datetime.utcnow()

  def connection_lost(self, exc):
    self.connections.discard(self)
    self._timeout_handler.cancel()
    self.cleanup()

  def cleanup(self):
    self.websocket = None
    self.transport = None
    self.timeout = 10
    self.max_size = 1
    self.max_queue = 1
    self.read_limit = 2 ** 16
    self.write_limit = 2 ** 16
    self.enabled = False
    self.url = None
    logger.warn('handle connections')
    self.connections = None
    self.request = None
    self.headers = None
    self.parser = None
    self._last_request_time = None
    self._request_handler_task = None

  def connection_timeout(self):
    time_elapsed = datetime.datetime.utcnow() - self._last_request_time
    seconds_elapsed = round(time_elapsed.seconds + float('0.%d' % time_elapsed.microseconds))
    if seconds_elapsed <= self.timeout:
      logger.info('Handler Timed out for WebSocket/Channel')

      #import ipdb; ipdb.set_trace()
      pass
      #if self._request_handler_task:
      #  self._request_handler_task.cancel()

      #exception = panic_exceptions.RequestTimeout('Request Timeout')
      #self.write_error(exception)

    else:
      time_left = self.timeout - seconds_elapsed
      self._timeout_handler = self.params.loop.call_later(time_left, self.connection_timeout)


  def data_received(self, data):
    try:
      if self.enabled:
        self.websocket.data_received(data)
      else:
        self.parser.feed_data(data)

    except HttpParserError as err:
      logger.debug(err)
      import ipdb; ipdb.set_trace()
      exception = panic_exceptions.InvalidUsage('Bad Request')
      self.write_error(exception)

    except HttpParserUpgrade as err:
      logger.debug(err)
      self.enabled = True

      response = panic_response.Response(b'')
      try:
        key = handshake.check_request(lambda x: self.headers.get(x).value)
        handshake.build_response(response.assimilate, key)
      except InvalidHandshake:
        exception = panic_exceptions.InvalidUsage('Invalid websocket request')
        self.write_error(exception)

      else:
        self.transport.write(response.channel('1.1'))
        self.websocket = WebSocketCommonProtocol(
            timeout=self.timeout,
            max_size=self.max_size,
            max_queue=self.max_queue,
            read_limit=self.read_limit,
            write_limit=self.write_limit)

        self.websocket.subprotocol = None
        #subprotocol
        self.websocket.connection_made(self.transport)
        self.websocket.connection_open()

        self._request_handler_task = self.params.loop.create_task(
            self.params.request_handler(self.request, self.websocket, self.transport))

  def on_url(self, url):
    self.url = url

  def on_message_complete(self):
    pass
    #self._request_handler = self.paramsself.params
    #self._request_handler_task = self.params.loop.create_task(
    #    self.params.request_handler(self.request, self.write_response))

  def on_header(self, name, value):
    self.headers.append(name.decode(), value.decode('utf-8'))

  def on_headers_complete(self):
    remote_addr = self.transport.get_extra_info('peername')
    if remote_addr:
      self.headers.append(remote_addr[0], str(remote_addr[1]))

    self.request = panic_request.Request(
      url = self.url,
      headers = self.headers,
      version = self.parser.get_http_version(),
      method = panic_datatypes.HTTPMethod.channel
    )

  def write_response(self, response):
    self.transport.close()

  def request_timeout_callback(self):
    if self.websocket is None:
      return super(WebSocketProtocol, self).request_timeout_callback()

  def write_error(self, exception):
    try:
      response = self.params.error_handler(self.request, exception)
      version = self.request.version if self.request else '1.1'
      self.transport.write(response.output(float(version)))
      self.transport.close()
    except Exception as err:
      # logger.exception(err)
      import traceback
      traceback.print_stack()
      import ipdb;ipdb.set_trace()
      self.signal.stopped 
      import sys; sys.exit(1)
      self.bail_out("Writing error failed, connection closed {}".format(e))

class HttpProtocol(asyncio.Protocol):
  # http://book.pythontips.com/en/latest/__slots__magic.html
  # def __init__(self, *, loop, request_handler, error_handler, signal, connections, request_timeout) -> None:
  def __init__(self, params: panic_datatypes.ServerParams):
    self.params = params
    self.loop = params.loop
    self.transport = None
    self.request = None
    self.parser = None
    self.url = None
    self.headers = None
    self.signal = params.signal
    self.connections = params.connections
    self.request_handler = params.request_handler
    self.request_timeout = params.request_timeout
    self._total_request_size = 0
    self._timeout_handler = None
    self._last_request_time = None
    self._request_handler_task = None
    self._identity = uuid.uuid4()

  # -------------------------------------------- #
  # Connection
  # -------------------------------------------- #
  def connection_made(self, transport):
    self.connections.add(self)
    self._timeout_handler = self.loop.call_later(self.request_timeout, self.connection_timeout)
    self.transport = transport
    self._last_request_time = datetime.datetime.utcnow()

  def connection_lost(self, exc):
    self.connections.discard(self)
    self._timeout_handler.cancel()
    self.cleanup()

  def connection_timeout(self):
    time_elapsed = datetime.datetime.utcnow() - self._last_request_time
    try:
      if time_elapsed.seconds < self.request_timeout:
        time_left = self.request_timeout - time_elapsed.seconds
        self._timeout_handler = self.loop.call_later(time_left, self.connection_timeout)
    except Exception as err:
      print(err)
      import ipdb; ipdb.set_trace()
      pass

    else:
      if self._request_handler_task:
        self._request_handler_task.cancel()

      exception = panic_exceptions.RequestTimeout('Request Timeout')
      self.write_error(exception)

  # -------------------------------------------- #
  # Parsing
  # -------------------------------------------- #

  def data_received(self, data):
    # Check for the request itself getting too large and exceeding
    # memory limits
    # TODO: ^
    self._total_request_size += len(data)

    # Create parser if this is the first time we're receiving data
    if self.parser is None:
      assert self.request is None
      self.headers = panic_datatypes.HTTPHeaders()
      self.parser = HttpRequestParser(self)

    # Parse request chunk or close connection
    try:
      self.parser.feed_data(data)
    except HttpParserError as err:
      import ipdb;ipdb.set_trace()
      exception = panic_exceptions.InvalidUsage('Bad Request')
      self.write_error(exception)

  def on_url(self, url):
    self.url = url

  def on_header(self, name, value):
    #if name == b'Content-Length' and int(value) > 1000:
    #  exception = PayloadTooLarge('Payload Too Large')
    #  self.write_error(exception)

    self.headers.append(name.decode(), value.decode('utf-8'))

  def on_headers_complete(self):
    remote_addr = self.transport.get_extra_info('peername')
    if remote_addr:
      self.headers.append(remote_addr[0], str(remote_addr[1]))

    self.request = panic_request.Request(
      url = self.url,
      headers = self.headers,
      version = self.parser.get_http_version(),
      method = panic_datatypes.HTTPMethod.Match(self.parser.get_method().decode())
    )

  def on_body(self, body):
    self.request.body.append(body)

  def on_message_complete(self):
    self._request_handler_task = self.loop.create_task(self.request_handler(self.request, self.write_response))

  # -------------------------------------------- #
  # Responding
  # -------------------------------------------- #

  def write_response(self, response):
    if self.parser:
      keep_alive = self.parser.should_keep_alive() and not self.signal.stopped

    else:
      keep_alive = False

    try:
      self.transport.write(response.output(getattr(self.request, 'version', '1.1')))
    except RuntimeError as err:
      logger.error(err)

    except Exception as err:
      import ipdb; ipdb.set_trace()
      pass

    if keep_alive:
      self._last_request_time = datetime.datetime.utcnow()
      self.cleanup()

    else:
      self.transport.close()

  def write_error(self, exception):
    try:
      response = self.params.error_handler(self.request, exception)
      version = self.request.version if self.request else '1.1'
      self.transport.write(response.output(float(version)))
      self.transport.close()
    except panic_exceptions.RequestTimeout:
      exception = panic_exceptions.ServerError('RT')
      exception.status = 408
      response = self.params.error_handler(self.request, exception)
      version = self.request.version if self.request else '1.1'
      self.transport.write(response.output(float(version)))
      self.transport.close()
      #self.write_error(exception)

    except Exception as err:
      # logger.exception(err)
      import traceback
      traceback.print_stack()
      import ipdb;ipdb.set_trace()
      import sys; sys.exit(1)
      self.bail_out("Writing error failed, connection closed {}".format(e))

  def bail_out(self, message):
    exception = ServerError(message)
    self.write_error(exception)
    logger.error(message)

  def cleanup(self):
    self.parser = None
    self.request = None
    self.url = None
    self.headers = None
    self._request_handler_task = None

  def close_if_idle(self):
    """
    Close the connection if a request is not being sent or received
    :return: boolean - True if closed, false if staying open
    """
    if not self.parser:
      self.transport.close()
      return True

    return False

