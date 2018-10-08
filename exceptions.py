from panic import response as panic_response


class PanicRouteExists(Exception):
  pass

class MissingRequiredHeader(PanicRouteExists):
  pass

class PanicException(Exception):
  def __init__(self, message, status_code=None):
    super().__init__(message)
    if status_code is not None:
      self.status_code = status_code

class NotFound(PanicException):
  status = 404

class BadRequest(PanicException):
  status = 400

class InvalidUsage(PanicException):
  status = 400

class ServerError(PanicException):
  status = 500

class FileNotFound(NotFound):
  status = 404

  def __init__(self, message, path, relative_url):
    super().__init__(message)
    self.path = path
    self.relative_url = relative_url

class RequestTimeout(PanicException):
  status = 408

class PayloadTooLarge(PanicException):
  status = 413

class InvalidHTTPMethod(PanicException):
  status = 405

