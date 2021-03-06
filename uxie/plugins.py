import weakref

class Injector(object):
    def __init__(self, activator, plugin_manager):
        self.activator = activator
        self.plugin_manager = plugin_manager

    def ready(self, name, obj):
        return self.plugin_manager.ready(name, obj)

    def done(self, name, obj):
        return self.plugin_manager.done(name, obj)

    def on_ready(self, name, callback):
        return self.plugin_manager.on_ready(name, callback)

    def on_done(self, name, callback):
        return self.plugin_manager.on_done(name, callback)

    def on(self, *context):
        return self.activator.on(*context)

    def bind(self, ctx, name, menu_entry, callback, *args):
        return self.activator.bind(ctx, name, menu_entry, callback, *args)

    def bind_check(self, ctx, name, menu_entry, callback, *args):
        return self.activator.bind_check(ctx, name, menu_entry, callback, *args)

    def bind_menu(self, menu_entry):
        return self.activator.bind_menu(menu_entry)

    def bind_dynamic(self, ctx, name, menu_entry, generator, resolver, as_radio=False):
        return self.activator.bind_dynamic(ctx, name, menu_entry, generator, resolver, as_radio)

    def map(self, ctx, name, accel, priority=None):
        return self.activator.map(ctx, name, accel, priority)

    def add_context(self, ctx, depends, callback):
        return self.activator.add_context(ctx, depends, callback)


class Manager(object):
    def __init__(self, activator):
        self.plugins = []
        self.ready_callbacks = {}
        self.ready_objects = {}
        self.done_callbacks = {}
        self.injector = Injector(activator, self)

    def add_plugin(self, plugin):
        self.plugins.append(plugin)
        try:
            plugin.init(self.injector)
        except:
            import traceback
            traceback.print_exc()

    def ready(self, name, obj):
        self.ready_objects.setdefault(name, weakref.WeakKeyDictionary())[obj] = True
        if name in self.ready_callbacks:
            for c in self.ready_callbacks[name]:
                c(obj)

    def done(self, name, obj):
        try:
            del self.ready_objects[name][obj]
        except KeyError:
            pass

        if name in self.done_callbacks:
            for c in self.done_callbacks[name]:
                c(obj)

    def on_ready(self, name, callback):
        if name in self.ready_objects:
            map(callback, self.ready_objects[name])

        self.ready_callbacks.setdefault(name, []).append(callback)

    def on_done(self, name, callback):
        self.done_callbacks.setdefault(name, []).append(callback)
