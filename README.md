# `importlib.resources`
This repository is to house the design and implementation of a planned
`importlib.resources` module for Python's stdlib -- aiming for
Python 3.7 -- along with a backport to target Python 3.4 - 3.6.

The key goal of this module is to replace
[`pkg_resources`](https://setuptools.readthedocs.io/en/latest/pkg_resources.html)
with a solution in Python's stdlib that relies on well-defined APIs.
This should not only make reading resources included in packages easier,
but have the semantics be stable and consistent.

## Goals
- Provide a reasonable replacement for `pkg_resources.resource_stream()`
- Provide a reasonable replacement for `pkg_resources.resource_string()`
- Provide a reasonable replacement for `pkg_resources.resource_filename()`
- Define an ABC for loaders to implement for reading resources
- Implement this in the stdlib for Python 3.7
- Implement a package for PyPI which will work on Python >=3.4

## Non-goals
- Replace all of `pkg_resources`
- For what is replaced in `pkg_resources`, provide an **exact**
  replacement

# Design

## Low-level
For [`importlib.abc`](https://docs.python.org/3/library/importlib.html#module-importlib.abc):
```python
from typing import Optional
from typing.io import BinaryIO


class ResourceReader(abc.ABC):

    def open_resource(self, path) -> BinaryIO:
        """Return a file-like object opened for binary reading.

        The path is expected to be relative to the location of the
        package this loader represents.
        """
        raise FileNotFoundError

    def resource_path(self, path) -> str:
        """Return the file system path to the specified resource.

        If the resource does not exist on the file system, raise
        FileNotFoundError.
        """
        raise FileNotFoundError
```

## High-level
For `importlib.resources`:
```python
import contextlib
import importlib
import os
import pathlib
import tempfile
import types
from typing import ContextManager, Iterator, Union
from typing.io import BinaryIO


Package = Union[str, types.ModuleType]
FileName = Union[str, os.PathLike]


<<<<<<< HEAD
def _get_package(package_name):
    module = importlib.import_module(package_name)
    if module.__spec__.submodule_search_locations is None:
        raise TypeError(f"{package_name!r} is not a package")
=======
def _get_package(package):
    if hasattr(package, '__spec__'):
        if package.__spec__.submodule_search_locations is None:
            raise TypeError(f"{package.__spec__.name!r} is not a package")
        else:
            return package
>>>>>>> master
    else:
        module = importlib.import_module(package_name)
        if module.__spec__.submodule_search_locations is None:
            raise TypeError(f"{package_name!r} is not a package")
        else:
            return module


def _normalize_path(path):
    directory, file_name = os.path.split(path)
    if directory:
        raise ValueError(f"{path!r} is not just a file name")
    else:
        return file_name


<<<<<<< HEAD
def open(package_name: str, path: Path) -> BinaryIO:
    """Return a file-like object opened for binary-reading of the resource."""
    normalized_path = _normalize_path(path)
    module = _get_package(package_name)
    return module.__spec__.loader.open_resource(normalized_path)


def read(package_name: str, path: Path, encoding: str = "utf-8",
=======
def open(module_name: Package, file_name: FileName) -> BinaryIO:
    """Return a file-like object opened for binary-reading of the resource."""
    normalized_path = _normalize_path(file_name)
    module = _get_package(module_name)
    return module.__spec__.loader.open_resource(normalized_path)


def read(module_name: Package, file_name: FileName, encoding: str = "utf-8",
>>>>>>> master
         errors: str = "strict") -> str:
    """Return the decoded string of the resource.

    The decoding-related arguments have the same semantics as those of
    bytes.decode().
    """
<<<<<<< HEAD
    with open(package_name, path) as file:
=======
    # Note this is **not** builtins.open()!
    with open(module_name, file_name) as file:
>>>>>>> master
        return file.read().decode(encoding=encoding, errors=errors)


@contextlib.contextmanager
<<<<<<< HEAD
def path(package_name: str, path: Path) -> Iterator[pathlib.Path]:
=======
def path(module_name: Package, file_name: FileName) -> Iterator[pathlib.Path]:
>>>>>>> master
    """A context manager providing a file path object to the resource.

    If the resource does not already exist on its own on the file system,
    a temporary file will be created. If the file was created, the file
    will be deleted upon exiting the context manager (no exception is
    raised if the file was deleted prior to the context manager
    exiting).
    """
<<<<<<< HEAD
    normalized_path = _normalize_path(path)
    module = _get_package(package_name)
=======
    normalized_path = _normalize_path(file_name)
    module = _get_package(module_name)
>>>>>>> master
    try:
        yield pathlib.Path(module.__spec__.resource_path(normalized_path))
    except FileNotFoundError:
        with module.__spec__.open_resource(normalized_path) as file:
            data = file.read()
        raw_path = tempfile.mkstemp()
        try:
            with open(raw_path, 'wb') as file:
                file.write(data)
            yield pathlib.Path(raw_path)
        finally:
            try:
                os.delete(raw_path)
            except FileNotFoundError:
                pass
```

<<<<<<< HEAD
If *package_name* has not been imported yet then it will be as a
side-effect of the call. The specified module is expected to be a
package, otherwise `TypeError` is raised. The module is expected to
have a loader specified on `__spec__.loader` which
=======
If *package* is an actual package, it is used directly. Otherwise the
argument is used in calling `importlib.import_module()`. The found
package is expected to be an actual package, otherwise `TypeError` is
raised.
>>>>>>> master

For the *file_name* argument, it is expected to be only a file name
with no other path parts. If any parts beyond a file name are found, a
`ValueError` will be raised. The expectation is that all data files
will exist within a directory that can be imported by Python as a
package.

All functions raise `FileNotFoundError` if the resource does not exist
or cannot be found.


# Open Issues
Please see the
[issue tracker](https://github.com/brettcannon/importlib_resources/issues).
