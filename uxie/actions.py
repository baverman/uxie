import gtk

def get_accel_path(name):
    return '<Actions>/' + name

class Activator(object):
    def __init__(self):
        self.accel_group = gtk.AccelGroup()
        self.actions = {}
        self.shortcuts = {}

    def attach(self, window):
        window.add_accel_group(self.accel_group)

    def map(self, name, accel):
        key, modifier = km = gtk.accelerator_parse(accel)
        gtk.accel_map_change_entry(get_accel_path(name), key, modifier, True)
        self.shortcuts.setdefault(km, []).append(name)

    def bind(self, name, desc, callback, *args):
        self.actions[name] = (desc, callback, args)
        self.accel_group.connect_by_path(get_accel_path(name), self.activate)

    def bind_accel(self, name, desc, accel, callback, *args):
        self.bind(name, desc, callback, *args)
        self.map(name, accel)

    def get_callback_and_args(self, *key):
        return self.actions[self.shortcuts[key][0]][1:]

    def activate(self, group, window, key, modifier):
        cb, args = self.get_callback_and_args(key, modifier)
        result = cb(*args)
        return result is None or result
