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

    def get_ctx_and_name(self, name):
        ctx, _, name = name.partition('/')
        return ctx, name

    def bind_accel(self, name, desc, accel, callback, *args):
        ctx, name = self.get_ctx_and_name(name)
        self.bind(name, desc, callback, *args)
        self._map(ctx, name, accel)

    def map(self, name, accel):
        ctx, name = self.get_ctx_and_name(name)
        self._map(ctx, name, accel)

    def _map(self, ctx, name, accel):
        key, modifier = km = gtk.accelerator_parse(accel)
        if key == 0:
            import warnings
            warnings.warn("Can't parse %s" % accel)

        self.accel_group.connect_group(key, modifier, gtk.ACCEL_VISIBLE, self.activate)
        self.shortcuts.setdefault(km, []).append((ctx, name))

    def activate(self, group, window, key, modifier):
        key_ctx, path = self.shortcuts[(key, modifier)][0]
        ctx, ctx_obj = self.context_resolver.get_context(window)

        if ctx == key_ctx or key_ctx == 'any':
            cb, args = self.actions[path][1:]

            result = cb(ctx_obj, *args)
            return result is None or result
        else:
            return False