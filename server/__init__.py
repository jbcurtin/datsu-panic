import asyncio
import logging
import time

from functools import partial
from signal import SIGINT, SIGTERM

from panic import \
    datatypes as panic_datatypes

logger = logging.getLogger(__name__)
current_time = None

def update_current_time(loop):
    """
    Caches the current time, since it is needed
    at the end of every keep-alive request to update the request timeout time

    :param loop:
    :return:
    """
    global current_time
    current_time = time.time()
    loop.call_later(1, partial(update_current_time, loop))


def serve(params: panic_datatypes.ServerParams) -> None:
  logger.info(f'Goin\' Fast @ http://{params.host}:{params.port}')

  server = partial(params.protocol, params)
  #  params.protocol,
  #  para
  #  loop=params.loop,
  #  connections=params.connections,
  #  signal=params.signal,
  #  request_handler=params.request_handler,
  #  error_handler=params.error_handler,
  #  request_timeout=params.request_timeout
  #)

  server_coroutine = params.loop.create_server(
    server,
    host=params.host,
    port=params.port,
    reuse_port=params.reuse_port)
  #sock=params.sock)

  params.loop.call_soon(partial(update_current_time, params.loop))

  try:
    http_server = params.loop.run_until_complete(server_coroutine)
  except Exception:
    logger.exception("Unable to start server")
    return

  # Register signals for graceful termination
  for _signal in (SIGINT, SIGTERM):
    params.loop.add_signal_handler(_signal, params.loop.stop)

  try:
    params.loop.run_forever()
  finally:
    logger.info("Stop requested, draining connections...")

    # Wait for event loop to finish and all connections to drain
    http_server.close()
    params.loop.run_until_complete(http_server.wait_closed())

    # Complete all tasks on the loop
    params.signal.stopped = True
    for connection in params.connections:
      connection.close_if_idle()

    while params.connections:
      params.loop.run_until_complete(asyncio.sleep(0.1))

    params.loop.close()

