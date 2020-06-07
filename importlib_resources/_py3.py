import os
import sys

from . import abc as resources_abc
from . import _common
from contextlib import contextmanager, suppress
from importlib.abc import ResourceLoader
from io import BytesIO, TextIOWrapper
from pathlib import Path
from types import ModuleType
from typing import Iterable, Iterator, Optional, Set, Union   # noqa: F401
from typing import cast
from typing.io import BinaryIO, TextIO

if False:  # TYPE_CHECKING
    from typing import ContextManager

Package = Union[ModuleType, str]
if sys.version_info >= (3, 6):
    Resource = Union[str, os.PathLike]              # pragma: <=35
else:
    Resource = str                                  # pragma: >=36


def _normalize_path(path) -> str:
    """Normalize a path by ensuring it is a string.

    If the resulting string contains path separators, an exception is raised.
    """
    str_path = str(path)
    parent, file_name = os.path.split(str_path)
    if parent:
        raise ValueError('{!r} must be only a file name'.format(path))
    return file_name


def _get_resource_reader(
        package: ModuleType) -> Optional[resources_abc.ResourceReader]:
    # Return the package's loader if it's a ResourceReader.  We can't use
    # a issubclass() check here because apparently abc.'s __subclasscheck__()
    # hook wants to create a weak reference to the object, but
    # zipimport.zipimporter does not support weak references, resulting in a
    # TypeError.  That seems terrible.
    spec = package.__spec__
    reader = getattr(spec.loader, 'get_resource_reader', None)
    if reader is None:
        return None
    return cast(resources_abc.ResourceReader, reader(spec.name))


def open_binary(package: Package, resource: Resource) -> BinaryIO:
    """Return a file-like object opened for binary reading of the resource."""
    resource = _normalize_path(resource)
    package = _common.get_package(package)
    reader = _get_resource_reader(package)
    if reader is not None:
        return reader.open_resource(resource)
    # Using pathlib doesn't work well here due to the lack of 'strict'
    # argument for pathlib.Path.resolve() prior to Python 3.6.
    absolute_package_path = os.path.abspath(
        package.__spec__.origin or 'non-existent file')
    package_path = os.path.dirname(absolute_package_path)
    full_path = os.path.join(package_path, resource)
    try:
        return open(full_path, mode='rb')
    except OSError:
        # Just assume the loader is a resource loader; all the relevant
        # importlib.machinery loaders are and an AttributeError for
        # get_data() will make it clear what is needed from the loader.
        loader = cast(ResourceLoader, package.__spec__.loader)
        data = None
        if hasattr(package.__spec__.loader, 'get_data'):
            with suppress(OSError):
                data = loader.get_data(full_path)
        if data is None:
            package_name = package.__spec__.name
            message = '{!r} resource not found in {!r}'.format(
                resource, package_name)
            raise FileNotFoundError(message)
        return BytesIO(data)


def open_text(package: Package,
              resource: Resource,
              encoding: str = 'utf-8',
              errors: str = 'strict') -> TextIO:
    """Return a file-like object opened for text reading of the resource."""
    return TextIOWrapper(
        open_binary(package, resource), encoding=encoding, errors=errors)


def read_binary(package: Package, resource: Resource) -> bytes:
    """Return the binary contents of the resource."""
    with open_binary(package, resource) as fp:
        return fp.read()


def read_text(package: Package,
              resource: Resource,
              encoding: str = 'utf-8',
              errors: str = 'strict') -> str:
    """Return the decoded string of the resource.

    The decoding-related arguments have the same semantics as those of
    bytes.decode().
    """
    with open_text(package, resource, encoding, errors) as fp:
        return fp.read()


def path(
        package: Package, resource: Resource,
        ) -> 'ContextManager[Path]':
    """A context manager providing a file path object to the resource.

    If the resource does not already exist on its own on the file system,
    a temporary file will be created. If the file was created, the file
    will be deleted upon exiting the context manager (no exception is
    raised if the file was deleted prior to the context manager
    exiting).
    """
    reader = _get_resource_reader(_common.get_package(package))
    return (
        _path_from_reader(reader, resource)
        if reader else
        _common.as_file(
            _common.files(package).joinpath(_normalize_path(resource)))
        )


@contextmanager
def _path_from_reader(reader, resource):
    norm_resource = _normalize_path(resource)
    with suppress(FileNotFoundError):
        yield Path(reader.resource_path(norm_resource))
        return
    opener_reader = reader.open_resource(norm_resource)
    with _common._tempfile(opener_reader.read, suffix=norm_resource) as res:
        yield res


def is_resource(package: Package, name: str) -> bool:
    """True if `name` is a resource inside `package`.

    Directories are *not* resources.
    """
    package = _common.get_package(package)
    _normalize_path(name)
    reader = _get_resource_reader(package)
    if reader is not None:
        return reader.is_resource(name)
    package_contents = set(contents(package))
    if name not in package_contents:
        return False
    return (_common.from_package(package) / name).is_file()


def contents(package: Package) -> Iterable[str]:
    """Return an iterable of entries in `package`.

    Note that not all entries are resources.  Specifically, directories are
    not considered resources.  Use `is_resource()` on each entry returned here
    to check if it is a resource or not.
    """
    package = _common.get_package(package)
    reader = _get_resource_reader(package)
    if reader is not None:
        return reader.contents()
    # Is the package a namespace package?  By definition, namespace packages
    # cannot have resources.
    namespace = (
        package.__spec__.origin is None or
        package.__spec__.origin == 'namespace'
        )
    if namespace or not package.__spec__.has_location:
        return ()
    return list(item.name for item in _common.from_package(package).iterdir())
