import os
import typing

class CaseInsensitiveDict:
  headers: typing.List[str]

  def __init__(self, headers: typing.Tuple[str, str]) -> None:
    self._headers = headers

  def __setitem__(self, name, value):
    raise KeyError(f'{name} is not allowed to be set')
    self._headers[name.lower()] = value

  def __getitem__(self, name):
    try:
      return self._headers[name.lower()]
    except KeyError as err:
      raise KeyError(f'{name} is not a valid key')

