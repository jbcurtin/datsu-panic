import inspect
import re
import typing

from collections import defaultdict
from functools import lru_cache
from panic import \
    exceptions as panic_exceptions, \
    datatypes as panic_datatypes, \
    request as panic_request

from panic.router import datatypes as router_datatypes

CACHE_SIZE = 1024
REGEX_TYPES = {
  'string': (str, r'[^/]+'),
  'int': (int, r'\d+'),
  'number': (float, r'[0-9\\.]+'),
  'alpha': (str, r'[A-Za-z]+'),
}

class Router:
  _routes: typing.Dict[str, router_datatypes.URIRoute]

  def __init__(self, service: object):
    self._service = service
    self.methods = {method.name.lower():method for method in service.params.supported_methods}
    self._routes = {}

  def __contains__(self, item):
    return item in self._routes

  def _method_factory(self, method_name):
    if method_name in ['channel']:
      def _wrapper(url, socket_encoding, socket_protocol):
        def _handler(handler):
          route = router_datatypes.URIRoute(url, panic_datatypes.HTTPMethod.channel, handler,
              inspect.iscoroutinefunction(handler),
              inspect.isasyncgenfunction(handler),
              socket_encoding, socket_protocol)

          if route in self:
            raise panic_exceptions.InvalidRoute(f'Route[{route}] already exists.')

          self._routes[route.identity] = route

          return handler
        return _handler
      return _wrapper

    else:
      def _wrapper(url):
        def _handler(handler):
          #import ipdb;ipdb.set_trace()
          route = router_datatypes.URIRoute(url, panic_datatypes.HTTPMethod.Match(method_name), handler,
              inspect.iscoroutinefunction(handler),
              inspect.isasyncgenfunction(handler))
          if route in self:
            raise panic_exceptions.InvalidRoute(f'Route[{route}] already exists.')

          self._routes[route.identity] = route
          return handler
  
        return _handler
      return _wrapper

  # Server API
  # lru-cache
  def get(self, method: panic_datatypes.HTTPMethod, url: str) -> router_datatypes.URIRoute:
    route_identity = hash(router_datatypes.URIRoute.route_hasher(url, method))
    try:
      return self._routes[route_identity]
    except KeyError as err:
      try:
        route_identity = hash(router_datatypes.URIRoute.route_hasher(url, panic_datatypes.HTTPMethod.channel))
        self._routes[route_identity]
        raise panic_exceptions.InvalidHTTPMethod(method, url)
      except KeyError as err:
        raise panic_exceptions.NotFound(url)

      except AttributeError as err:
        raise panic_exceptions.NotFound(url)



class RouterAPI:
  _router: Router
  def __init__(self, panic_service: object) -> None:
    self._router = Router(panic_service)

  def __getattr__(self, name) -> typing.Any:
    if name in self._router.methods:
      return self._router._method_factory(name)

    if name in ['request']:
      return self._router.get

    raise panic_exceptions.InvalidHTTPMethod(name)

  #@lru_cache(maxsize=CACHE_SIZE)
  #def get(self, url, method):
  #  """
  #  Gets a request handler based on the URL of the request, or raises an
  #  error.  Internal method for caching.
  #  :param url: Request URL
  #  :param method: Request method
  #  :return: handler, arguments, keyword arguments
  #  """
  #  # Check against known static routes
  #  route = self.routes_static.get(url)
  #  if route:
  #    match = route.pattern.match(url)
  #  else:
  #    # Move on to testing all regex routes
  #    for route in self.routes_dynamic[url_hash(url)]:
  #      match = route.pattern.match(url)
  #      if match:
  #        break
  #    else:
  #      # Lastly, check against all regex routes that cannot be hashed
  #      for route in self.routes_always_check:
  #        match = route.pattern.match(url)
  #        if match:
  #          break
  #      else:
  #        raise panic_exceptions.NotFound(f'Requested URL {url} not found')

  #  if route.methods and method not in route.methods:
  #    raise panic_exceptions.InvalidUsage(f'Method {method} not allowed for URL {url}', status_code=405)
  #  kwargs = {p.name: p.cast(value)
  #      for value, p
  #      in zip(match.groups(1), route.parameters)}

  #  return route.handler, [], kwargs
