class Manager(object):
    def __init__(self, activator):
        self.activator = activator
        self.plugins = []
        self.ready_callbacks = {}
        self.ready_objects = {}

    def add_plugin(self, plugin):
        self.plugins.append(plugin)
        plugin.init(self.activator, self)

    def ready(self, name, obj):
        self.ready_objects.setdefault(name, []).append(obj)
        if name in self.ready_callbacks:
            for c in self.ready_callbacks[name]:
                c(obj)

    def on_ready(self, name, callback):
        if name in self.ready_objects:
            map(callback, self.ready_objects[name])

        self.ready_callbacks.setdefault(name, []).append(callback)