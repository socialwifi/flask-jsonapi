
class NotImplementedProperty:
    def __init__(self, key):
        self.key = key

    def __get__(self, instance, owner):
        if self.key not in instance.__dict__:
            raise NotImplementedError
        else:
            return instance.__dict__[self.key]

    def __set__(self, instance, value):
        instance.__dict__[self.key] = value
