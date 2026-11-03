"""
Objects created when first used.

The knowledge database and the user database need the website's database,
which the website provides through :class:`~lmfdb_utils.site.Site` once it has
started; so they are created the first time they are used, rather than when
their modules are imported.
"""

import threading


class LazyObject:
    """
    A stand-in for the object returned by ``factory()``, which is called the
    first time an attribute is read, set or deleted.  Afterward everything is
    forwarded to that object.
    """
    def __init__(self, factory, description="object"):
        object.__setattr__(self, "_lazy_factory", factory)
        object.__setattr__(self, "_lazy_description", description)
        object.__setattr__(self, "_lazy_instance", None)
        object.__setattr__(self, "_lazy_lock", threading.Lock())

    def _lazy_get(self):
        instance = object.__getattribute__(self, "_lazy_instance")
        if instance is None:
            with object.__getattribute__(self, "_lazy_lock"):
                instance = object.__getattribute__(self, "_lazy_instance")
                if instance is None:
                    instance = object.__getattribute__(self, "_lazy_factory")()
                    object.__setattr__(self, "_lazy_instance", instance)
        return instance

    def __getattr__(self, name):
        return getattr(self._lazy_get(), name)

    def __setattr__(self, name, value):
        setattr(self._lazy_get(), name, value)

    def __delattr__(self, name):
        delattr(self._lazy_get(), name)

    def __getitem__(self, key):
        return self._lazy_get()[key]

    def __bool__(self):
        return True

    def __repr__(self):
        instance = object.__getattribute__(self, "_lazy_instance")
        if instance is None:
            return "%s (created when first used)" % object.__getattribute__(self, "_lazy_description")
        return repr(instance)
