# -*- coding: utf-8 -*-
from bisect import bisect
import gtk
from gtk.keysyms import F2, Escape, Control_L, Control_R, Alt_L, Alt_R, Shift_L, Shift_R
from gtk.gdk import SHIFT_MASK, CONTROL_MASK, MOD1_MASK, SUPER_MASK

from .utils import make_missing_dirs

ANY_CTX = ('any', )
DEFAULT_PRIORITY = 0

gtk.accelerator_set_default_mod_mask(SHIFT_MASK | CONTROL_MASK | MOD1_MASK | SUPER_MASK)

def parse_accel(accel, priority=None):
    if priority is None:
        priority = DEFAULT_PRIORITY

    key, modifier = km = gtk.accelerator_parse(accel)
    if key == 0:
        import warnings
        warnings.warn("Can't parse %s" % accel)

    return km, priority


class KeyMap(object):
    def __init__(self, config_filename=None):
        self.generic_shortcuts = {}
        self.config = {}
        self.config_filename = config_filename

        if config_filename:
            self._load()

        self.changed_generics = self.config.setdefault('generic', {})
        self.default_generics = {}
        self._map_changed_generics()

    def _load(self):
        self.config.clear()
        try:
            execfile(self.config_filename, {}, self.config)
        except IOError:
            pass
        except:
            import traceback
            traceback.print_exc()

    def _map_changed_generics(self):
        for name, r in self.changed_generics.iteritems():
            for accel, priority in r:
                self._map_generic(name, accel, priority)

    def _map_generic(self, name, accel, priority=None):
        self.generic_shortcuts.setdefault(name, []).append(parse_accel(accel, priority))

    def map_generic(self, name, accel, priority=None):
        if name in self.changed_generics:
            self.default_generics.setdefault(name, []).append(parse_accel(accel, priority))
        else:
            self._map_generic(name, accel, priority)

    def get_activator(self, window=None, config_section=None):
        config = self.config.setdefault(config_section, {}) if config_section else {}
        return Activator(self, window, config)

    def replace_generics(self, name, keys):
        if name in self.default_generics and set(self.default_generics[name]) == set(keys):
            if name in self.changed_generics:
                del self.changed_generics[name]
        else:
            self.changed_generics[name] = [(gtk.accelerator_name(*km), pr) for km, pr in keys]

        self.generic_shortcuts.setdefault(name, [])[:] = []
        for km, pr in keys:
            self.generic_shortcuts[name].append((km, pr))

    def save(self):
        if not self.config_filename:
            return

        make_missing_dirs(self.config_filename)
        with open(self.config_filename, 'w') as f:
            for section, data in self.config.iteritems():
                if section.startswith('_'):
                    continue

                print >> f, '%s = {' % section
                for name, shortcuts in data.iteritems():
                    print >> f, '    %s: %s,' % (repr(name), repr(shortcuts))
                print >> f, '}\n'

class ContextHolder(object):
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
    def __init__(self, keymap, window=None, changed_shortcuts=None):
        self.accel_group = gtk.AccelGroup()
        self.actions = {}
        self.shortcuts = {}
        self.contexts = {}
        self.menu_entries = [[], {}, 0, 'Root']
        self.dyn_menu = {}

        self.keymap = keymap
        self.generic_shortcuts = keymap.generic_shortcuts

        self.default_shortcuts = {}
        self.changed_shortcuts = changed_shortcuts
        self._map_changed_shortcuts()

        self.bind(('window', 'activator'), 'root-menu', 'Root menu', show_actions_menu(''))
        self.bind_menu(('window', 'activator'), 'show-menu', None, None, actions_menu_resolver)

        if window:
            self.attach(window)

    def attach(self, window):
        window.add_accel_group(self.accel_group)
        window.connect('key-press-event', self.on_key_press)

    def on_key_press(self, window, event):
        key = event.keyval, event.state
        try:
            if key in self.shortcuts and self.shortcuts[key][0][0] < 0:
                return False
        except IndexError:
            pass

        w = window.get_focus()
        if w:
            if w.event(event):
                return True

        return False

    def on(self, *context):
        return ContextHolder(self, context)

    def normalize_context(self, ctx):
        if isinstance(ctx, tuple):
            return ctx
        else:
            return (ctx,)

    def _map_changed_shortcuts(self):
        if self.changed_shortcuts:
            for (ctx, name), r in self.changed_shortcuts.iteritems():
                for accel, priority in r:
                    self._map(ctx, name, accel, priority)

    def bind_accel(self, ctx, name, menu_entry, accel, callback, priority=None, *args):
        ctx = self.normalize_context(ctx)
        self.bind(ctx, name, menu_entry, callback, *args)
        self.map(ctx, name, accel, priority)

    def _add_shortcut(self, km, ctx, name, priority, is_generic=False):
        shortcuts = self.shortcuts.setdefault(km, [])
        if not shortcuts:
            self.accel_group.connect_group(km[0], km[1], gtk.ACCEL_VISIBLE, self.activate)

        shortcuts.insert(bisect(shortcuts, priority), (priority, ctx, name, is_generic))

    def get_menu_entry_list(self, entries, label, new_value):
        label, _, idx = label.partition('#')
        entry = label.replace('_', '')
        try:
            return entries[1][entry]
        except KeyError:
            pass

        if new_value:
            if not idx:
                idx = entries[2]
            else:
                idx = int(idx)

            entries[2] = idx
            entries[0].insert(bisect([i for i, e in entries[0]], idx), (idx, entry))

            v = new_value(label)
            entries[1][entry] = v
            return v
        else:
            raise KeyError(label)

    def add_menu_entry(self, menu_entry, ctx=None, name=None):
        items = menu_entry.split('/')
        entries = self.menu_entries

        new_submenu = lambda l: [[], {}, 1, l]
        for r in items[:-1]:
            entries = self.get_menu_entry_list(entries, r, new_submenu)

        if items[-1]:
            assert ctx is not None and name
            self.get_menu_entry_list(entries, items[-1], lambda l:(ctx, name, l))

    def bind(self, ctx, name, menu_entry, callback, *args):
        ctx = self.normalize_context(ctx)
        self.actions.setdefault(ctx, {})[name] = callback, args, menu_entry

        if menu_entry:
            self.add_menu_entry(menu_entry, ctx, name)

        if name in self.generic_shortcuts:
            for km, priority in self.generic_shortcuts[name]:
                self._add_shortcut(km, ctx, name, -priority, True)

    def bind_menu(self, ctx, name, menu_entry, generator, resolver):
        ctx = self.normalize_context(ctx)
        name = '!' + name

        if menu_entry:
            self.add_menu_entry(menu_entry + '/_entries', ctx, name)

        self.actions.setdefault(ctx, {})[name] = generator, resolver, menu_entry

    def map_menu(self, path, accel, priority=None):
        self.map(('window', 'activator'), '!show-menu/' + path, accel, priority)

    def _map(self, ctx, name, accel, priority=None):
        km, priority = parse_accel(accel, priority)
        self._add_shortcut(km, ctx, name, -priority, False)

    def map(self, ctx, name, accel, priority=None):
        assert ctx is not None
        ctx = self.normalize_context(ctx)
        key = ctx, name
        if key in self.changed_shortcuts:
            self.default_shortcuts.setdefault(key, []).append(parse_accel(accel, priority))
        else:
            self._map(ctx, name, accel, priority)

    def replace_keys(self, ctx, name, keys):
        key = ctx, name
        if key in self.default_shortcuts and set(self.default_shortcuts[key]) == set(keys):
            if key in self.default_shortcuts:
                del self.default_shortcuts[key]
        else:
            self.changed_shortcuts[key] = [(gtk.accelerator_name(*km), pr) for km, pr in keys]

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

        window.last_shortcut = key, modifier

        for pr, ctx, name, _ in self.shortcuts[(key, modifier)]:
            if pr > found_priority:
                break

            ctx_obj = self._find_context(ctx, cache)
            if ctx_obj is not None:
                try:
                    cb, args, label = self.actions[ctx][name]
                    args = ctx_obj + args
                except KeyError:
                    if name[0] == '!':
                        dname, _, param = name.partition('/')
                        _, resolver, menu_path = self.actions[ctx][dname]
                        cb, args, label = resolver(*(ctx_obj + (param,)))
                        if not cb:
                            continue

                        if menu_path:
                            label = menu_path + '/' + label
                    else:
                        raise KeyError('%s %s' % (ctx, name))

                actions.append((ctx, name, label, cb, args))
                if pr < found_priority:
                    found_priority = pr

        if actions:
            if len(actions) == 1:
                _, _, _, cb, args = actions[0]
                result = cb(*args)
                return result is None or result
            else:
                show_dups_menu(actions, window, self, cache)

        return False

    def activate_menu_item(self, item):
        item.get_parent().tr_window.last_shortcut = None, None

        ctx, name, obj = item.activate_context
        if item.contains_all_run_data:
            cb, args = obj
            cb(*args)
        else:
            if name.startswith('!'):
                obj()
            else:
                cb, args, _ = self.actions[ctx][name]
                cb(*(obj + args))

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
        if ctx == ANY_CTX:
            return ()

        if isinstance(ctx, tuple):
            result = tuple(self._find_context(r, cache) for r in ctx)
            return None if any(r is None for r in result) else result

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
                if d is None:
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
        return {'window':window, 'activator':self}

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

            for _, entry in entries:
                if not path and entry == 'Root menu': continue

                v = data[entry]
                if isinstance(v, list):
                    yield v[-1], 'menu', False, (path + entry, get_actions(v, path + entry))
                else:
                    ctx, name, label = v
                    ctx_obj = self._find_context(ctx, cache)
                    if ctx_obj is not None:
                        if name.startswith('!'):
                            cb, args, _ = self.actions[ctx][name]
                            for lb, action_name, cb_and_args in cb(*ctx_obj):
                                yield (lb, 'item', True,
                                    (ctx, '%s/%s' % (name, action_name), cb_and_args))
                        else:
                            yield label, 'item', False, (ctx, name, ctx_obj)

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

    for label, t, ard, v in actions:
        if t == 'item':
            acontext = v
            submenu = None
        else:
            acontext = ('window', 'activator'), '!show-menu/' + v[0]
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

        item.contains_all_run_data = ard

        item.activate_context = acontext
        item.connect_after('select', on_item_select, True)
        item.connect_after('deselect', on_item_select, False)
        menu.append(item)

    menu.connect('key-press-event', activator.on_menu_key_press)
    menu.show_all()

def actions_menu_resolver(window, activator, path=''):
    return show_actions_menu(path), (window, activator), path

def popup_menu(menu, window):
    def get_coords(menu):
        win = window.window
        x, y, w, h, _ = win.get_geometry()
        x, y = win.get_origin()
        mw, mh = menu.size_request()
        return x + w - mw, y + h - mh, False

    if menu.get_children():
        menu.popup(None, None, get_coords, 0, gtk.get_current_event_time())

def show_actions_menu(path=''):
    def inner(window, activator):
        actions = activator.get_allowed_actions(window, path)

        menu = gtk.Menu()
        fill_menu(menu, window, activator, actions)
        popup_menu(menu, window)

    return inner

def show_dups_menu(dups, window, activator, context_cache):
    actions = []
    for ctx, name, label, cb, args in dups:
        label = label.replace('_', '').replace('$', '')
        if name.startswith('!show-menu/'):
            actions.append((label, 'menu', False,
                (label, activator.get_allowed_actions(window, label, context_cache))))

        else:
            actions.append((label, 'item', True, (ctx, name, (cb, args))))

    menu = gtk.Menu()
    fill_menu(menu, window, activator, actions)
    popup_menu(menu, window)

def wait_mod_unpress_for_last_shortcut(window, callback):
    key, mod = window.last_shortcut
    hid = getattr(window, 'mod_unpress_handler_id', None)
    wmod = getattr(window, 'mod_unpress_value', None)
    if mod:
        if hid:
            if not wmod:
                window.handler_unblock(hid)
        else:
            window.mod_unpress_handler_id = window.connect('key-release-event',
                wait_mod_unpress_on_window_key_release)

        window.mod_unpress_value = mod
        window.mod_unpress_callback = callback
        return True
    else:
        if hid and wmod:
            window.handler_block(hid)
            window.mod_unpress_value = None

        return False

def wait_mod_unpress_on_window_key_release(window, event):
    wmod = window.mod_unpress_value
    mod = event.state & (CONTROL_MASK | SHIFT_MASK | MOD1_MASK)
    keyval = event.keyval

    if keyval == Shift_L or keyval == Shift_R:
        mod &= ~SHIFT_MASK

    if keyval == Control_L or keyval == Control_R:
        mod &= ~CONTROL_MASK

    if keyval == Alt_L or keyval == Alt_R:
        mod &= ~MOD1_MASK

    if wmod != mod:
        window.handler_block(window.mod_unpress_handler_id)
        window.mod_unpress_value = None
        cb = window.mod_unpress_callback
        window.mod_unpress_callback = None
        cb()

    return False

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

        if name in self.activator.generic_shortcuts:
            view, self.default_model = self.create_view(('default',),
                self.activator.generic_shortcuts[name])
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
        label.set_markup(', '.join(ctx) + ':')
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
            self.activator.keymap.replace_generics(name, list(self.get_keys(self.default_model)))

        self.activator.replace_keys(ctx, name, list(self.get_keys(self.ctx_model)))
        self.activator.keymap.save()

    def on_key_press_event(self, window, event):
        if event.keyval == Escape:
            self.quit()
            self.destroy()
            return True

        return False
