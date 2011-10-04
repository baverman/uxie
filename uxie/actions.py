# -*- coding: utf-8 -*-
from bisect import bisect
import gtk
from gtk.keysyms import F2

class ContextHolder():
    def __init__(self, activator, context):
        self.activator = activator
        self.context = context

    def map(self, name, accel, priority=None):
        self.activator.map(self.context, name, accel, priority)

    def bind(self, name, menu_entry, callback, *args):
        self.activator.bind(self.context, name, menu_entry, callback, *args)

    def bind_accel(self, name, menu_entry, accel, callback, priority=None, *args):
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
        self.menu_entries = [[], {}, 0, 'Root']
        self.dyn_menu = {}

        self.bind_accel('window-activator', 'root-menu', 'Root menu',
            '<ctrl>1', show_actions_menu(''))

        self.bind_menu('window-activator', 'show-menu', None, None, show_actions_menu)

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

    def bind_accel(self, ctx, name, menu_entry, accel, callback, priority=None, *args):
        self.bind(ctx, name, menu_entry, callback, *args)
        self.map(ctx, name, accel, priority)

    def _add_shortcut(self, km, ctx, name, priority):
        shortcuts = self.shortcuts.setdefault(km, [])
        shortcuts.insert(bisect(shortcuts, priority), (priority, ctx, name))

    def get_menu_entry_list(self, entries, label, new_value):
        entry = label.replace('_', '').lstrip('$')
        try:
            return entries[1][entry]
        except KeyError:
            pass

        if new_value:
            if label.startswith('$'):
                entries[2] += 1
                entries[0].append(entry)
            else:
                idx = len(entries[0]) - entries[2]
                entries[0].insert(idx, entry)

            v = new_value(label.lstrip('$'))
            entries[1][entry] = v
            return v
        else:
            raise KeyError(label)

    def add_menu_entry(self, ctx, name, menu_entry):
        items = menu_entry.split('/')
        entries = self.menu_entries

        new_submenu = lambda l: [[], {}, 0, l]
        for r in items[:-1]:
            entries = self.get_menu_entry_list(entries, r, new_submenu)

        self.get_menu_entry_list(entries, items[-1], lambda l:(ctx, name, l))

    def bind(self, ctx, name, menu_entry, callback, *args):
        self.actions.setdefault(ctx, {})[name] = callback, args
        self.add_menu_entry(ctx, name, menu_entry)

        if name in self.generic_shortcuts:
            for km, priority in self.generic_shortcuts[name]:
                self._add_shortcut(km, ctx, name, -priority)

    def bind_menu(self, ctx, name, menu_entry, generator, resolver):
        name = '!' + name

        if menu_entry:
            menu_entry = menu_entry + '/_entries'
            self.add_menu_entry(ctx, name, menu_entry)

        self.actions.setdefault(ctx, {})[name] = generator, resolver

    def map_menu(self, path, accel, priority=None):
        self.map('window-activator', '!show-menu/' + path, accel, priority)

    def map(self, ctx, name, accel, priority=None):
        if priority is None:
            priority = 0

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
                try:
                    cb, args = self.actions[ctx][name]
                except KeyError:
                    if name[0] == '!':
                        name, _, param = name.partition('/')
                        _, resolver = self.actions[ctx][name]
                        cb, args = resolver(param), ()
                    else:
                        raise KeyError('%s %s' % (ctx, name))

                result = cb(ctx_obj, *args)
                return result is None or result

        return False

    def activate_menu_item(self, item):
        ctx, name, obj = item.activate_context
        if name.startswith('!'):
            obj()
        else:
            cb, args = self.actions[ctx][name]
            cb(obj, *args)

    def on_menu_key_press(self, menu, event):
        if event.keyval == F2:
            item = getattr(menu, 'current_item', None)
            if item:
                print item.activate_context, self.get_km_for_action(*item.activate_context[:2])
                return True

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
        cache = {'window':window, 'window-activator':(window, self)}

        def get_actions(entries, path):
            entries, data, _, _ = entries
            if path:
                path += '/'

            for entry in entries:
                if not path and entry == 'Root menu': continue

                v = data[entry]
                if isinstance(v, list):
                    yield v[-1], 'menu', (path + entry, get_actions(v, path + entry))
                else:
                    ctx, name, label = v
                    ctx_obj = self._find_context(ctx, cache)
                    if ctx_obj:
                        if name.startswith('!'):
                            cb, args = self.actions[ctx][name]
                            for lb, action_name, action_cb in cb(ctx_obj):
                                yield (lb, 'item',
                                    (ctx, '%s/%s' % (name, action_name), action_cb))
                        else:
                            yield label, 'item', (ctx, name, ctx_obj)

        entries = self.menu_entries
        if path:
            for r in path.split('/'):
                entries = self.get_menu_entry_list(entries, r, None)

        return get_actions(entries, path)

    def add_context(self, ctx, depends, callback):
        if isinstance(depends, str):
            depends = (depends,)
        self.contexts[ctx] = depends, callback

def on_item_select(item, is_select):
    item.get_parent().current_item = item if is_select else None

def fill_menu(menu, window, activator, actions):
    menu.set_reserve_toggle_size(False)

    def activate_sub_menu(item, items):
        menu = item.get_submenu()
        if not getattr(menu, 'already_filled', None):
            fill_menu(menu, window, activator, items)
            menu.already_filled = True

    for label, t, v in actions:
        if t == 'item':
            km = activator.get_km_for_action(*v[:2])
            submenu = None
        else:
            km = None
            submenu = gtk.Menu()

        if km:
            item = gtk.MenuItem(None, True)
            box = gtk.HBox(False, 20)
            label = gtk.Label(label)
            label.set_alignment(0, 0.5)
            label.set_use_underline(True)
            box.pack_start(label)

            full_accel_str = ', '.join(gtk.accelerator_get_label(*r) for r in km)
            if len(km) > 1:
                accel_label = gtk.Label(gtk.accelerator_get_label(*km[0]) + '>')
                accel_label.set_tooltip_text(full_accel_str)
            else:
                accel_label = gtk.Label(full_accel_str)

            accel_label.set_alignment(1, 0.5)
            accel_label.modify_fg(gtk.STATE_NORMAL, accel_label.style.fg[gtk.STATE_INSENSITIVE])
            accel_label.modify_fg(gtk.STATE_PRELIGHT, accel_label.style.fg[gtk.STATE_INSENSITIVE])
            box.pack_start(accel_label)
            item.add(box)
        else:
            item = gtk.MenuItem(label, True)

        if submenu:
            item.activate_context = 'window-activator', '!show-menu/' + v[0]
            item.set_submenu(submenu)
            item.connect('activate', activate_sub_menu, v[1])
        else:
            item.activate_context = v
            item.connect('activate', activator.activate_menu_item)

        item.connect_after('select', on_item_select, True)
        item.connect_after('deselect', on_item_select, False)
        menu.append(item)

    menu.connect('key-press-event', activator.on_menu_key_press)
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