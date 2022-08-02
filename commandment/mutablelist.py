"""
Copyright (c) 2015 Jesse Peterson, 2017 Mosen
Licensed under the MIT license. See the included LICENSE.txt file for details.
"""
try:
    from sqlalchemy.ext.mutable import MutableList
except ImportError:
    # MutableList didn't make it into SQLAlchemy 1.0.12
    # This function copied directly from SQLAlchemy source
    from sqlalchemy.ext.mutable import Mutable

    class MutableList(Mutable, list):
        """A list type that implements :class:`.Mutable`.

        The :class:`.MutableList` object implements a list that will
        emit change events to the underlying mapping when the contents of
        the list are altered, including when values are added or removed.

        Note that :class:`.MutableList` does **not** apply mutable tracking to  the
        *values themselves* inside the list. Therefore it is not a sufficient
        solution for the use case of tracking deep changes to a *recursive*
        mutable structure, such as a JSON structure.  To support this use case,
        build a subclass of  :class:`.MutableList` that provides appropriate
        coersion to the values placed in the dictionary so that they too are
        "mutable", and emit events up to their parent structure.

        .. versionadded:: 1.1

        .. seealso::

            :class:`.MutableDict`

            :class:`.MutableSet`

        """

        def __setitem__(self, index, value):
            """Detect list set events and emit change events."""
            list.__setitem__(self, index, value)
            self.changed()

        def __setslice__(self, start, end, value):
            """Detect list set events and emit change events."""
            list.__setslice__(self, start, end, value)
            self.changed()

        def __delitem__(self, index):
            """Detect list del events and emit change events."""
            list.__delitem__(self, index)
            self.changed()

        def __delslice__(self, start, end):
            """Detect list del events and emit change events."""
            list.__delslice__(self, start, end)
            self.changed()

        def pop(self, *arg):
            result = list.pop(self, *arg)
            self.changed()
            return result

        def append(self, x):
            list.append(self, x)
            self.changed()

        def extend(self, x):
            list.extend(self, x)
            self.changed()

        def insert(self, i, x):
            list.insert(self, i, x)
            self.changed()

        def remove(self, i):
            list.remove(self, i)
            self.changed()

        def clear(self):
            list.clear(self)
            self.changed()

        def sort(self):
            list.sort(self)
            self.changed()

        def reverse(self):
            list.reverse(self)
            self.changed()

        @classmethod
        def coerce(cls, index, value):
            """Convert plain list to instance of this class."""
            if isinstance(value, cls):
                return value
            return cls(value) if isinstance(value, list) else Mutable.coerce(index, value)

        def __getstate__(self):
            return list(self)

        def __setstate__(self, state):
            self[:] = state
