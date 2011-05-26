from bisect import bisect
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

class ContextHolder():
    def __init__(self, activator, context):
        self.activator = activator
        self.context = context

    def map(self, name, accel, priority=0):
        self.activator.map(self.context, name, accel, priority)

    def bind(self, name, desc, callback, *args):
        self.activator.bind(self.context, name, desc, callback, *args)

    def bind_accel(self, name, desc, accel, callback, priority=0, *args):
        self.activator.bind_accel(self.context, name, desc, accel, callback, priority, *args)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class ContextActivator(Activator):
    def __init__(self, context_resolver):
        Activator.__init__(self)
        self.context_resolver = context_resolver
        self.generic_shortcuts = {}

    def attach(self, window):
        window.add_accel_group(self.accel_group)
        window.connect('key-press-event', self.on_key_press)

    def on_key_press(self, window, event):
        w = window.get_focus()
        if w:
            if w.event(event):
                return True

        return False

    def on(self, context):
        return ContextHolder(self, context)

    def bind_accel(self, ctx, name, desc, accel, callback, priority=0, *args):
        self.bind(ctx, name, desc, callback, *args)
        self.map(ctx, name, accel, priority)

    def _add_shortcut(self, km, ctx, name, priority):
        shortcuts = self.shortcuts.setdefault(km, [])
        shortcuts.insert(bisect(shortcuts, priority), (priority, ctx, name))

    def bind(self, ctx, name, desc, callback, *args):
        self.actions.setdefault(ctx, {})[name] = (desc, callback, args)
        if name in self.generic_shortcuts:
            for km, priority in self.generic_shortcuts[name]:
                self._add_shortcut(km, ctx, name, -priority)

    def map(self, ctx, name, accel, priority=0):
        key, modifier = km = gtk.accelerator_parse(accel)
        if key == 0:
            import warnings
            warnings.warn("Can't parse %s" % accel)

        self.accel_group.connect_group(key, modifier, gtk.ACCEL_VISIBLE, self.activate)
        if ctx is None:
            self.generic_shortcuts.setdefault(name, []).append((km, priority))
        else:
            self._add_shortcut(km, ctx, name, -priority)

    def activate(self, group, window, key, modifier):
        _, ctx, name = self.shortcuts[(key, modifier)][0]
        ctx_obj = self.context_resolver.get_context(window, ctx)

        if ctx_obj:
            cb, args = self.actions[ctx][name][1:]
            result = cb(ctx_obj, *args)
            return result is None or result
        else:
            return False