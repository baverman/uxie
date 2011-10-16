import time
import weakref
from bisect import bisect

class Escapable(object):
    def __init__(self, callback, *args):
        self.callback = callback
        self.args = map(weakref.ref, args)

    def cancel(self):
        args = [a() for a in self.args]
        self.callback(*args)

    def is_active(self):
        args = [a() for a in self.args]
        return not any(a is None for a in args)


class Manager(object):
    def __init__(self):
        self.escape_stack = []

    def push(self, obj, priority=None):
        if priority is None:
            priority = 0

        item = (-priority, time.time(), obj)
        self.escape_stack.insert(bisect(self.escape_stack, item), item)
        return obj

    def process(self):
        while self.escape_stack:
            _, _, obj = self.escape_stack.pop()
            if obj.is_active():
                obj.cancel()
                return False

        return True