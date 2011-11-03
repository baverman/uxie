import os, sys
from os.path import join, dirname, exists, expanduser

import weakref

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

def send_focus_change(widget, is_in):
    event = gtk.gdk.Event(gtk.gdk.FOCUS_CHANGE)
    event.window = widget.window
    event.in_ = is_in
    widget.send_focus_change(event)

def human_size(num):
    for x in ['bytes','KB','MB','GB','TB']:
        if num < 1024.0:
            return "%g %s" % (round(num, 1), x)
        num /= 1024.0


class WeakCallback(object):
    def __init__(self, obj, func, idle):
        self.wref = weakref.ref(obj)
        self.func = func
        self.gobject_token = None
        self.idle = idle

    def __call__(self, *args, **kwargs):
        obj = self.wref()
        if obj:
            if self.idle is False or self.idle is None:
                return self.func(obj, *args, **kwargs)
            elif self.idle is True:
                idle(self.func, *((obj,)+args), **kwargs)
            else:
                idle(self.func, priority=self.idle, *((obj,)+args), **kwargs)

        elif self.gobject_token:
            sender = args[0]
            sender.disconnect(self.gobject_token)
            self.gobject_token = None

        return False


def _idle_call(*args):
    callback, arguments, priority = args[-3:]
    args = args[:-3] + arguments
    if priority is True:
        idle(callback, *args)
    else:
        idle(callback, priority=idle, *args)

    return False

def connect(sender, signal, callback, idle=False, after=False, *args):
    try:
        obj = callback.im_self
    except AttributeError:
        if idle is not False:
            cb, args = _idle_call, (callback, args, idle)

        if after:
            return sender.connect_after(signal, cb, *args)
        else:
            return sender.connect(signal, cb, *args)

    wc = WeakCallback(obj, callback.im_func, idle)
    if after:
        wc.gobject_token = sender.connect_after(signal, wc, *args)
    else:
        wc.gobject_token = sender.connect(signal, wc, *args)

    return wc.gobject_token

def lazy_func(name):
    globs = sys._getframe(1).f_globals
    def inner(*args, **kwargs):
        try:
            func = inner.func
        except AttributeError:
            module, _, func_name = name.rpartition('.')
            module_name = module.lstrip('.')
            level = len(module) - len(module_name)
            module = __import__(module_name, globals=globs, level=level)
            func = inner.func = getattr(module, func_name)

        return func(*args, **kwargs)

    return inner