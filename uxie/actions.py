from bisect import bisect
import gtk
import itertools

class ContextHolder():
    def __init__(self, activator, context):
        self.activator = activator
        self.context = context

    def map(self, name, accel, priority=0):
        self.activator.map(self.context, name, accel, priority)

    def bind(self, name, menu_entry, callback, *args):
        self.activator.bind(self.context, name, menu_entry, callback, *args)

    def bind_accel(self, name, menu_entry, accel, callback, priority=0, *args):
        self.activator.bind_accel(self.context, name, menu_entry, accel, callback, priority, *args)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class Activator(object):
    def __init__(self):
        self.accel_group = gtk.AccelGroup()
        self.actions = {}
        self.shortcuts = {}
        self.generic_shortcuts = {}
        self.contexts = {}
        self.menu_entries = {}

        self.bind_accel('window-activator', 'root-menu', 'Root menu',
            '<ctrl>1', show_actions_menu())

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

    def bind_accel(self, ctx, name, menu_entry, accel, callback, priority=0, *args):
        self.bind(ctx, name, menu_entry, callback, *args)
        self.map(ctx, name, accel, priority)

    def _add_shortcut(self, km, ctx, name, priority):
        shortcuts = self.shortcuts.setdefault(km, [])
        shortcuts.insert(bisect(shortcuts, priority), (priority, ctx, name))

    def bind(self, ctx, name, menu_entry, callback, *args):
        self.actions.setdefault(ctx, {})[name] = callback, args
        self.menu_entries.setdefault(ctx, {})[name] = menu_entry
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
        for _, ctx, name in self.shortcuts[(key, modifier)]:
            ctx_obj = self.get_context(window, ctx)
            if ctx_obj:
                cb, args = self.actions[ctx][name]
                result = cb(ctx_obj, *args)
                return result is None or result

        return False

    def _find_context(self, ctx, cache):
        try:
            return cache[ctx]
        except KeyError:
            pass

        try:
            depends, callback = self.contexts[ctx]
        except KeyError:
            print 'There are no any registered providers for [%s] context' % ctx
            return None

        if depends:
            args = []
            for dctx in depends:
                d = self._find_context(dctx, cache)
                if not d:
                    result = None
                    break

                args.append(d)
            else:
                result = callback(*args)
        else:
            result = callback()

        cache[ctx] = result
        return result

    def get_context(self, window, ctx):
        return self._find_context(ctx, {'window':window, 'window-activator':(window, self)})

    def get_km_for_action(self, ctx, name):
        result = []
        for km, actions in self.shortcuts.iteritems():
            for _, actx, aname in actions:
                if ctx == actx and name == aname:
                    result.append(km)

                break

        return result

    def get_allowed_actions(self, window, path):
        cache = {'window':window}

        if path and not path.endswith('/'):
            path = path + '/'

        plen = len(path)

        actions = {}

        for ctx in itertools.chain(('window',), self.contexts):
            ctx_obj = self._find_context(ctx, cache)
            if ctx_obj:
                for name, entry in self.menu_entries.get(ctx, {}).items():
                    if entry.startswith(path):
                        items = entry[plen:].split('/')
                        p = actions
                        for r in items[:-1]:
                            p = p.setdefault(r, {})

                        p[items[-1]] = ctx, name

        return actions

    def add_context(self, ctx, depends, callback):
        if isinstance(depends, str):
            depends = (depends,)
        self.contexts[ctx] = depends, callback

def fill_menu(menu, window, activator, actions):
    menu.set_reserve_toggle_size(False)

    for label, v in sorted(actions.items(), key=lambda r: r[0].replace('_', '')):
        if isinstance(v, tuple):
            km = activator.get_km_for_action(*v)
            submenu = None
        else:
            km = None
            submenu = gtk.Menu()

        if km:
            item = gtk.MenuItem(None, True)
            box = gtk.HBox(False, 5)
            label = gtk.Label(label)
            label.set_alignment(0, 0.5)
            label.set_use_underline(True)
            box.pack_start(label)

            accel_label = gtk.Label(', '.join(gtk.accelerator_get_label(*r) for r in km))
            accel_label.set_alignment(1, 0.5)
            accel_label.modify_fg(gtk.STATE_NORMAL, accel_label.style.fg[gtk.STATE_INSENSITIVE])
            accel_label.modify_fg(gtk.STATE_PRELIGHT, accel_label.style.fg[gtk.STATE_INSENSITIVE])
            box.pack_start(accel_label)
            item.add(box)
        else:
            item = gtk.MenuItem(label, True)

        if submenu:
            item.set_submenu(submenu)

        menu.append(item)

    menu.show_all()

def show_actions_menu(path=''):
    def inner(args):
        window, activator = args
        actions = activator.get_allowed_actions(window, path)

        def get_coords(menu):
            win = window.window
            x, y, w, h, _ = win.get_geometry()
            x, y = win.get_origin()
            mw, mh = menu.size_request()
            return x + w - mw, y + h - mh, False

        menu = gtk.Menu()
        fill_menu(menu, window, activator, actions)
        menu.popup(None, None, get_coords, 0, gtk.get_current_event_time())

    return inner