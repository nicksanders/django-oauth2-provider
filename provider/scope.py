"""
Default scope implementation relying on bit shifting. See
:attr:`provider.constants.SCOPES` for the list of available scopes.

Scopes can be combined, such as ``"read write"``. Note that a single
``"write"`` scope is *not* the same as ``"read write"``.

See :class:`provider.scope.to_int` on how scopes are combined.
"""

import operator
from functools import reduce
from .constants import SCOPES

SCOPE_CHOICES = [(value, name) for (value, name, verbose) in SCOPES]
SCOPE_NAMES = [(name, name) for (value, name, verbose) in SCOPES]
SCOPE_NAME_DICT = dict([(name, value) for (value, name, verbose) in SCOPES])
SCOPE_VALUE_DICT = dict([(value, name) for (value, name, verbose) in SCOPES])
SCOPE_VERBOSE_DICT = dict([(name, verbose) for (value, name, verbose) in SCOPES])


def check(wants, has):
    """
    Check if a desired scope ``wants`` is part of an available scope ``has``.

    Returns ``False`` if not, return ``True`` if yes.

    :example:

    If a list of scopes such as

    ::

        READ = 1 << 1
        WRITE = 1 << 2
        READ_WRITE = READ | WRITE

        SCOPES = (
            (READ, 'read'),
            (WRITE, 'write'),
            (READ_WRITE, 'read+write'),
        )

    is defined, we can check if a given scope is part of another:

    ::

        >>> from provider import scope
        >>> scope.check(READ, READ)
        True
        >>> scope.check(WRITE, READ)
        False
        >>> scope.check(WRITE, WRITE)
        True
        >>> scope.check(READ, WRITE)
        False
        >>> scope.check(READ, READ_WRITE)
        True
        >>> scope.check(WRITE, READ_WRITE)
        True

    """
    return (wants & has) == wants


def to_names(scope):
    """
    Returns a list of scope names as defined in
    :attr:`provider.constants.SCOPES` for a given scope integer.

        >>> assert ['read', 'write'] == provider.scope.names(provider.constants.READ_WRITE)

    """
    return [
        name
        for (name, value) in list(SCOPE_NAME_DICT.items())
        if check(value, scope)
    ]

# Keep it compatible
names = to_names


def to_int(*names, **kwargs):
    """
    Turns a list of scope names into an integer value.

    ::

        >>> scope.to_int('read')
        2
        >>> scope.to_int('write')
        6
        >>> scope.to_int('read', 'write')
        6
        >>> scope.to_int('invalid')
        0
        >>> scope.to_int('invalid', default = 1)
        1

    """

    return reduce(lambda prev, next: (prev | SCOPE_NAME_DICT.get(next, 0)),
            names, kwargs.pop('default', 0))

def decompose(scope):
    """
    Returns a list of masks given a combined scope value
    """
    return [s for s in SCOPE_VALUE_DICT if s & scope]

def compose(*scopes):
    """
    Returns a combined scope value given a list of masks
    """
    return reduce(operator.or_, scopes, 0)
