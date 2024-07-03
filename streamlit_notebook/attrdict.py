class AttrDict(dict):
    """
    A simple subclass of dict enabling attribute style access to items.

    This class allows dictionary items to be accessed using dot notation,
    in addition to the standard bracket notation.

    Methods:
        __getattr__(key): Allows accessing dictionary items as attributes.
        __setattr__(key, value): Allows setting dictionary items as attributes.
        __delattr__(key): Allows deleting dictionary items as attributes.
    """
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"{type(self).__name__} has no attribute '{key}'")

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError(f"{type(self).__name__} has no attribute '{key}'")