class AttrDict(dict):
    """
    A simple subclass of dict enabling attribute style access to items
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