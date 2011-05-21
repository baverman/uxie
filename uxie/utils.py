import os
from os.path import join, dirname, exists, expanduser

import gobject
import gtk

def idle_callback(callable, args):
    args, kwargs = args
    callable(*args, **kwargs)
    return False

def idle(callable, *args, **kwargs):
    options = {}
    if 'priority' in kwargs:
        options['priority'] = kwargs['priority']
        del kwargs['priority']
    return gobject.idle_add(idle_callback, callable, (args, kwargs), **options)

def join_to_file_dir(filename, *args):
    return join(dirname(filename), *args)

def join_to_settings_dir(*args):
    config_dir = os.getenv('XDG_CONFIG_HOME', expanduser('~/.config'))
    return join(config_dir, *args)

def join_to_data_dir(*args):
    config_dir = os.getenv('XDG_DATA_HOME', expanduser('~/.local/share'))
    return join(config_dir, *args)

def join_to_cache_dir(*args):
    config_dir = os.getenv('XDG_CACHE_HOME', expanduser('~/.cache'))
    return join(config_dir, *args)

def make_missing_dirs(filename):
    path = dirname(filename)
    if not exists(path):
        os.makedirs(path, mode=0755)

def refresh_gui():
    while gtk.events_pending():
        gtk.main_iteration_do(block=False)


class BuilderAware(object):
    def __init__(self, glade_file):
        self.gtk_builder = gtk.Builder()
        self.gtk_builder.add_from_file(glade_file)
        self.gtk_builder.connect_signals(self)

    def __getattr__(self, name):
        obj = self.gtk_builder.get_object(name)
        if not obj:
            raise AttributeError('Builder have no %s object' % name)

        setattr(self, name, obj)
        return obj