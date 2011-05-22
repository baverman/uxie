import gtk

class Activator(object):
    def __init__(self):
        self.accel_group = gtk.AccelGroup()
        self.actions = {}
        self.shortcuts = {}

    def attach(self, window):
        window.add_accel_group(self.accel_group)

    def map(self, name, accel):
        key, modifier = km = gtk.accelerator_parse(accel)
        if key == 0:
            import warnings
            warnings.warn("Can't parse %s" % accel)

        self.accel_group.connect_group(key, modifier, gtk.ACCEL_VISIBLE, self.activate)
        self.shortcuts.setdefault(km, []).append(name)

    def bind(self, name, desc, callback, *args):
        self.actions[name] = (desc, callback, args)

    def bind_accel(self, name, desc, accel, callback, *args):
        self.bind(name, desc, callback, *args)
        self.map(name, accel)

    def get_callback_and_args(self, *key):
        return self.actions[self.shortcuts[key][0]][1:]

    def activate(self, group, window, key, modifier):
        cb, args = self.get_callback_and_args(key, modifier)
        result = cb(*args)
        return result is None or result

class ContextActivator(Activator):
    def __init__(self, context_resolver):
        Activator.__init__(self)
        self.context_resolver = context_resolver

    def activate(self, group, window, key, modifier):
        cb, args = self.get_callback_and_args(key, modifier)
        ctx = self.context_resolver.get_context(window)
        result = cb(ctx, *args)
        return result is None or result
