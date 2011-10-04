# -*- coding: utf-8 -*-
from bisect import bisect
import gtk
from gtk.keysyms import F2, Escape

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

        self.bind_menu('window-activator', 'show-menu', None, None, actions_menu_resolver)

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

    def _add_shortcut(self, km, ctx, name, priority, is_generic=False):
        shortcuts = self.shortcuts.setdefault(km, [])
        if not shortcuts:
            self.accel_group.connect_group(km[0], km[1], gtk.ACCEL_VISIBLE, self.activate)

        shortcuts.insert(bisect(shortcuts, priority), (priority, ctx, name, is_generic))

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
        self.actions.setdefault(ctx, {})[name] = callback, args, menu_entry
        self.add_menu_entry(ctx, name, menu_entry)

        if name in self.generic_shortcuts:
            for km, priority in self.generic_shortcuts[name]:
                self._add_shortcut(km, ctx, name, -priority, True)

    def bind_menu(self, ctx, name, menu_entry, generator, resolver):
        name = '!' + name

        if menu_entry:
            self.add_menu_entry(ctx, name, menu_entry + '/_entries')

        self.actions.setdefault(ctx, {})[name] = generator, resolver, menu_entry

    def map_menu(self, path, accel, priority=None):
        self.map('window-activator', '!show-menu/' + path, accel, priority)

    def map(self, ctx, name, accel, priority=None):
        if priority is None:
            priority = 0

        key, modifier = km = gtk.accelerator_parse(accel)
        if key == 0:
            import warnings
            warnings.warn("Can't parse %s" % accel)

        if ctx is None:
            self.generic_shortcuts.setdefault(name, []).append((km, priority))
        else:
            self._add_shortcut(km, ctx, name, -priority, False)

    def replace_keys(self, ctx, name, keys):
        if not ctx:
            self.generic_shortcuts.setdefault(name, [])[:] = []
            for km, pr in keys:
                self.generic_shortcuts[name].append((km, pr))
        else:
            for km in self.shortcuts:
                actions = self.shortcuts[km]
                actions[:] = [r for r in actions if r[1] != ctx or r[2] != name]

                if not actions:
                    self.accel_group.disconnect_key(*km)

            for km, pr in self.generic_shortcuts.get(name, []):
                self._add_shortcut(km, ctx, name, -pr, True)

            for km, pr in keys:
                self._add_shortcut(km, ctx, name, -pr, False)

    def activate(self, group, window, key, modifier):
        found_priority = 10000
        actions = []
        cache = self.get_context_cache(window)

        for pr, ctx, name, _ in self.shortcuts[(key, modifier)]:
            if pr > found_priority:
                break

            ctx_obj = self._find_context(ctx, cache)
            if ctx_obj:
                try:
                    cb, args, label = self.actions[ctx][name]
                except KeyError:
                    if name[0] == '!':
                        name, _, param = name.partition('/')
                        _, resolver, menu_path = self.actions[ctx][name]
                        cb, label = resolver(param)
                        if menu_path:
                            label = menu_path + '/' + label
                        args = ()
                    else:
                        raise KeyError('%s %s' % (ctx, name))

                actions.append((ctx, name, label, cb, ctx_obj, args))
                if pr < found_priority:
                    found_priority = pr

        if actions:
            if len(actions) == 1:
                _, _, _, cb, ctx_obj, args
                result = cb(ctx_obj, *args)
                return result is None or result
            else:
                show_dups_menu(actions, window, self, cache)

        return False

    def activate_menu_item(self, item):
        ctx, name, obj = item.activate_context
        if name.startswith('!'):
            obj()
        else:
            cb, args, _ = self.actions[ctx][name]
            cb(obj, *args)

    def on_menu_key_press(self, menu, event):
        if event.keyval == F2:
            item = getattr(menu, 'current_item', None)
            if item:
                w = ShortcutChangeDialog(self, *item.activate_context[:2])
                w.set_transient_for(menu.tr_window)
                menu.cancel()
                w.show_all()

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

    def get_context_cache(self, window):
        return {'window':window, 'window-activator':(window, self)}

    def get_context(self, window, ctx):
        return self._find_context(ctx, self.get_context_cache(window))

    def get_km_for_action(self, ctx, name):
        result = []
        for km, actions in self.shortcuts.iteritems():
            for pr, actx, aname, is_generic in actions:
                if ctx == actx and name == aname:
                    result.append((km, pr, is_generic))

        return result

    def get_allowed_actions(self, window, path, cache=None):
        cache = cache or self.get_context_cache(window)

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
                            cb, args, _ = self.actions[ctx][name]
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
    menu.tr_window = window

    def activate_sub_menu(item, items):
        menu = item.get_submenu()
        if not getattr(menu, 'already_filled', None):
            fill_menu(menu, window, activator, items)
            menu.already_filled = True

    for label, t, v in actions:
        if t == 'item':
            acontext = v
            submenu = None
        else:
            acontext = 'window-activator', '!show-menu/' + v[0]
            submenu = gtk.Menu()

        km = activator.get_km_for_action(*acontext[:2])
        if km:
            item = gtk.MenuItem(None, True)
            box = gtk.HBox(False, 20)
            label = gtk.Label(label)
            label.set_alignment(0, 0.5)
            label.set_use_underline(True)
            box.pack_start(label)

            full_accel_str = ', '.join(gtk.accelerator_get_label(*r[0]) for r in km)
            if len(km) > 1:
                accel_label = gtk.Label(gtk.accelerator_get_label(*km[0][0]) + '>')
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
            item.set_submenu(submenu)
            item.connect('activate', activate_sub_menu, v[1])
        else:
            item.connect('activate', activator.activate_menu_item)

        item.activate_context = acontext
        item.connect_after('select', on_item_select, True)
        item.connect_after('deselect', on_item_select, False)
        menu.append(item)

    menu.connect('key-press-event', activator.on_menu_key_press)
    menu.show_all()

def actions_menu_resolver(path=''):
    return show_actions_menu(path), path

def popup_menu(menu, window):
    def get_coords(menu):
        win = window.window
        x, y, w, h, _ = win.get_geometry()
        x, y = win.get_origin()
        mw, mh = menu.size_request()
        return x + w - mw, y + h - mh, False

    menu.popup(None, None, get_coords, 0, gtk.get_current_event_time())

def show_actions_menu(path=''):
    def inner(args):
        window, activator = args
        actions = activator.get_allowed_actions(window, path)

        menu = gtk.Menu()
        fill_menu(menu, window, activator, actions)
        popup_menu(menu, window)

    return inner

def show_dups_menu(dups, window, activator, context_cache):
    actions = []
    for ctx, name, label, _, obj, _ in dups:
        label = label.replace('_', '').replace('$', '')
        if name == '!show-menu':
            actions.append((label, 'menu',
                (label, activator.get_allowed_actions(window, label, context_cache))))

        else:
            actions.append((label, 'item', (ctx, name, obj)))

    menu = gtk.Menu()
    fill_menu(menu, window, activator, actions)
    popup_menu(menu, window)


class ShortcutChangeDialog(gtk.Window):
    def __init__(self, activator, ctx, name):
        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
        self.set_modal(True)
        self.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.set_title('Change shortcut')
        self.set_border_width(5)
        self.connect('delete-event', self.quit)
        self.connect('key-press-event', self.on_key_press_event)

        self.activator = activator
        self.acontext = ctx, name

        box = gtk.VBox(False, 10)
        self.add(box)

        label = gtk.Label()
        label.set_markup('<b>Action:</b> ' + name)
        label.set_alignment(0, 0.5)
        label.set_width_chars(40)
        box.pack_start(label, False, False)

        if name in activator.generic_shortcuts:
            view, self.default_model = self.create_view('default', activator.generic_shortcuts[name])
            box.pack_start(view)
        else:
            self.default_model = None

        view, self.ctx_model = self.create_view(
            ctx, ((r[0], -r[1]) for r in activator.get_km_for_action(ctx, name) if not r[2]))
        box.pack_start(view)

    def add_rows_if_needed(self, model):
        for r in list(model):
            if r[0] == r[1] == 0:
                del model[r.path]

        model.append((0, 0, 0))

    def on_accel_edited(self, renderer, path, key, mod, code, model):
        model[path][0] = key
        model[path][1] = mod
        self.add_rows_if_needed(model)

    def on_accel_cleared(self, renderer, path, model):
        if model[path][0] == model[path][1] == 0:
            model[path][0], model[path][1] = gtk.accelerator_parse('BackSpace')
        else:
            model[path][0] = 0
            model[path][1] = 0

        self.add_rows_if_needed(model)

    def on_priority_edited(self, renderer, path, text, model):
        model[path][2] = int(text)

    def create_view(self, ctx, items):
        box = gtk.VBox(False, 5)

        label = gtk.Label()
        label.set_alignment(0, 0.5)
        label.set_markup(ctx + ':')
        box.pack_start(label, False, False)

        frame = gtk.Frame()
        box.pack_start(frame)

        model = gtk.ListStore(int, int, int)
        view = gtk.TreeView(model)
        view.set_headers_visible(False)
        view.set_border_width(5)
        frame.add(view)

        cell = gtk.CellRendererAccel()
        cell.props.editable = True
        cell.connect('accel-edited', self.on_accel_edited, model)
        cell.connect('accel-cleared', self.on_accel_cleared, model)
        view.append_column(gtk.TreeViewColumn('accel', cell, accel_key=0, accel_mods=1))

        cell = gtk.CellRendererText()
        cell.props.editable = True
        cell.props.xalign = 1
        cell.props.width_chars = 5
        cell.connect('edited', self.on_priority_edited, model)
        view.append_column(gtk.TreeViewColumn('priority', cell, text=2))

        for (key, mod), pr  in items:
            model.append((key, mod, pr))

        model.append((0, 0, 0))

        return box, model

    def get_keys(self, model):
        for r in model:
            if r[0]:
                yield (r[0], r[1]), r[2]

    def quit(self, *args):
        ctx, name = self.acontext
        if self.default_model:
            self.activator.replace_keys(None, name, list(self.get_keys(self.default_model)))

        self.activator.replace_keys(ctx, name, list(self.get_keys(self.ctx_model)))

    def on_key_press_event(self, window, event):
        if event.keyval == Escape:
            self.quit()
            self.destroy()
            return True

        return False
