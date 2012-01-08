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

    key, _modifier = km = gtk.accelerator_parse(accel)
    if key == 0:
        import warnings
        warnings.warn("Can't parse %s" % accel)

    return km, priority

def normalize_context(ctx):
    if isinstance(ctx, tuple):
        return ctx
    else:
        return (ctx,)


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
        self.default_generics.setdefault(name, []).append(parse_accel(accel, priority))
        if name not in self.changed_generics:
            self._map_generic(name, accel, priority)

    def get_activator(self, window=None, config_section=None):
        config = self.config.setdefault(config_section, {}) if config_section else {}
        return Activator(self, window, config)

    def replace_generics(self, name, keys):
        if name in self.default_generics and set(self.default_generics[name]) == set(keys):
            self.changed_generics.pop(name, None)
        else:
            if keys:
                self.changed_generics[name] = [(gtk.accelerator_name(*km), pr) for km, pr in keys]
            else:
                self.changed_generics.pop(name, None)

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
        return self.activator.bind(self.context, name, menu_entry, callback, *args)

    def bind_check(self, name, menu_entry, callback, *args):
        return self.activator.bind_check(self.context, name, menu_entry, callback, *args)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class AccelBinder(object):
    def __init__(self, activator, context, name):
        self.activator = activator
        self.context = context
        self.name = name

    def to(self, accel, priority=None):
        self.activator.map(self.context, self.name, accel, priority)
        return self


def create_entry_widget(cls, title, km):
    if km:
        item = cls(None, True)
        box = gtk.HBox(False, 20)
        label = gtk.Label(title)
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
        item = cls(title, True)

    return item


class BaseEntry(object):
    def __init__(self, ctx, name):
        self.ctx = ctx
        self.name = name
        self.title = 'Unknown'

    def get_widget(self, _ctx_getterm, km):
        return create_entry_widget(gtk.MenuItem, self.title, km)

    def __repr__(self):
        return 'Entry(%s, %s, %s)' % (self.ctx, self.name, self.title)

    def is_match(self, ctx_getter):
        ctx_obj = ctx_getter(self.ctx)
        return ctx_obj is not None


class Entry(BaseEntry):
    def __init__(self, ctx, name, callback, args):
        BaseEntry.__init__(self, ctx, name)
        self.callback = callback
        self.args = args

    def __call__(self, ctx_getter):
        ctx_obj = ctx_getter(self.ctx)
        return self.callback(*(ctx_obj + self.args))


class CheckEntry(Entry):
    def __call__(self, ctx_getter):
        ctx_obj = ctx_getter(self.ctx)
        return self.callback(*(ctx_obj + self.args))

    def get_widget(self, ctx_getter, km):
        widget = create_entry_widget(gtk.CheckMenuItem, self.title, km)
        ctx_obj = ctx_getter(self.ctx)
        widget.set_active(self.callback(*(ctx_obj + (False,) + self.args)))
        return widget

    def __call__(self, ctx_getter):
        ctx_obj = ctx_getter(self.ctx)
        return self.callback(*(ctx_obj + (True,) + self.args))


class DEntry(Entry):
    def __init__(self, ctx, name, title, callback, args):
        Entry.__init__(self, ctx, name, callback, args)
        self.title = title

    def __call__(self, _ctx_getter):
        return self.callback(*self.args)


class MultiEntry(BaseEntry):
    def __init__(self, ctx, name, generator, resolver):
        BaseEntry.__init__(self, ctx, name)
        self.generator = generator
        self.resolver = resolver

    def get_entries(self, ctx_getter):
        for title, eid, cb in self.generator(*ctx_getter(self.ctx)):
            yield DEntry(self.ctx, self.name + '/' + eid, title, *cb)

    def resolve(self, *args):
        result = self.resolver(*args)
        if result:
            cb, args, title = result
            return DEntry(self.ctx, None, title, cb, args)


class DRadioEntry(DEntry):
    def get_widget(self, _ctx_getter, km):
        widget = create_entry_widget(
            lambda label, underline:gtk.RadioMenuItem(None, label, underline), self.title, km)
        widget.set_active(self.is_active)
        return widget

class RadioEntry(MultiEntry):
    def get_entries(self, ctx_getter):
        for is_active, title, eid, cb in self.generator(*ctx_getter(self.ctx)):
            entry = DRadioEntry(self.ctx, self.name + '/' + eid, title, *cb)
            entry.is_active = is_active
            yield entry

    def resolve(self, *args):
        result = self.resolver(*args)
        if result:
            is_active, cb, args, title = result
            entry = DRadioEntry(self.ctx, None, title, cb, args)
            entry.is_active = is_active
            return entry


class MenuEntry(object):
    def __init__(self):
        self.entries = []
        self.items = {}
        self.idx = 0
        self.path = ''
        self.ctx = ('window', 'activator')

    def get_widget(self, _ctx_getter, km):
        return create_entry_widget(gtk.MenuItem, self.title, km)

    def get_entry(self, label, default=None, default_cb=None):
        label, _, idx = label.partition('#')
        entry = label.replace('_', '')
        try:
            return self.items[entry]
        except KeyError:
            pass

        if default_cb:
            default = default_cb()

        if default:
            if not idx:
                idx = self.idx
            else:
                idx = int(idx)

            self.idx = idx
            self.entries.insert(bisect([i for i, _ in self.entries], idx), (idx, entry))

            default.path = (self.path + '/' + entry) if self.path else entry
            default.title = label
            if isinstance(default, MenuEntry):
                default.name = '!show-menu/' + default.path
            self.items[entry] = default
            return default
        else:
            raise KeyError(label)

    def get_entry_for_path(self, path):
        if not path:
            return self

        entry = self
        for r in path.split('/'):
            entry = entry.get_entry(r)

        return entry

    def get_entries(self, ctx_getter):
        for _, e in self.entries:
            entry = self.items[e]
            if entry.is_match(ctx_getter):
                if isinstance(entry, MultiEntry):
                    for dentry in entry.get_entries(ctx_getter):
                        yield dentry
                else:
                    yield entry

    def is_match(*args):
        return True

    def __repr__(self):
        return 'MenuEntry(%s)' % self.path


class Activator(object):
    def __init__(self, keymap, window=None, changed_shortcuts=None):
        self.accel_group = gtk.AccelGroup()
        self.actions = {}
        self.shortcuts = {}
        self.contexts = {}
        self.menu = MenuEntry()
        self.dyn_menu = {}

        self.keymap = keymap
        self.generic_shortcuts = keymap.generic_shortcuts

        self.default_shortcuts = {}
        self.changed_shortcuts = changed_shortcuts
        self._map_changed_shortcuts()

        self.bind(('window', 'activator'), 'root-menu', None, show_actions_menu(''))
        self.bind_dynamic(('window', 'activator'), 'show-menu', None, None, actions_menu_resolver)

        if window:
            self.attach(window)

    def attach(self, window):
        window.add_accel_group(self.accel_group)
        window.connect('key-press-event', self.on_key_press)

    def on_key_press(self, window, event):
        key = event.keyval, event.state & ~8192
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

    def _map_changed_shortcuts(self):
        if self.changed_shortcuts:
            for (ctx, name), r in self.changed_shortcuts.iteritems():
                for accel, priority in r:
                    self._map(ctx, name, accel, priority)

    def _add_shortcut(self, km, ctx, name, priority, is_generic=False):
        shortcuts = self.shortcuts.setdefault(km, [])
        if not shortcuts:
            self.accel_group.connect_group(km[0], km[1], gtk.ACCEL_VISIBLE, self.activate)

        shortcuts.insert(bisect(shortcuts, priority), (priority, ctx, name, is_generic))

    def add_menu_entry(self, menu_entry, entry=None):
        new_submenu = lambda: MenuEntry()
        menu = self.menu
        items = menu_entry.split('/')
        for r in items[:-1]:
            menu = menu.get_entry(r, default_cb=new_submenu)

        if items[-1]:
            assert entry
            menu = menu.get_entry(items[-1], entry)

        return menu

    def bind(self, ctx, name, menu_entry, callback, *args):
        ctx = normalize_context(ctx)
        entry = self.actions.setdefault(ctx, {})[name] = Entry(ctx, name, callback, args)

        if menu_entry:
            self.add_menu_entry(menu_entry, entry)

        if name in self.generic_shortcuts:
            for km, priority in self.generic_shortcuts[name]:
                self._add_shortcut(km, ctx, name, -priority, True)

        return AccelBinder(self, ctx, name)

    def bind_check(self, ctx, name, menu_entry, callback, *args):
        ctx = normalize_context(ctx)
        entry = self.actions.setdefault(ctx, {})[name] = CheckEntry(ctx, name, callback, args)

        if menu_entry:
            self.add_menu_entry(menu_entry, entry)

        if name in self.generic_shortcuts:
            for km, priority in self.generic_shortcuts[name]:
                self._add_shortcut(km, ctx, name, -priority, True)

        return AccelBinder(self, ctx, name)

    def bind_menu(self, menu_entry):
        entry = self.add_menu_entry(menu_entry+'/')
        return AccelBinder(self, entry.ctx, entry.name)

    def bind_dynamic(self, ctx, name, menu_entry, generator, resolver, as_radio=False):
        ctx = normalize_context(ctx)
        name = '!' + name
        cls = RadioEntry if as_radio else MultiEntry
        entry = self.actions.setdefault(ctx, {})[name] = cls(ctx, name, generator, resolver)
        if menu_entry:
            self.add_menu_entry(menu_entry, entry)

    def _map(self, ctx, name, accel, priority=None):
        km, priority = parse_accel(accel, priority)
        self._add_shortcut(km, ctx, name, -priority, False)

    def map(self, ctx, name, accel, priority=None):
        assert ctx is not None
        ctx = normalize_context(ctx)
        key = ctx, name
        self.default_shortcuts.setdefault(key, []).append(parse_accel(accel, priority))
        if key not in self.changed_shortcuts:
            self._map(ctx, name, accel, priority)

    def replace_keys(self, ctx, name, keys):
        key = ctx, name
        if key in self.default_shortcuts and set(self.default_shortcuts[key]) == set(keys):
            self.changed_shortcuts.pop(key, None)
        else:
            if keys:
                self.changed_shortcuts[key] = [(gtk.accelerator_name(*km), pr) for km, pr in keys]
            else:
                self.changed_shortcuts.pop(key, None)

        for km in self.shortcuts:
            actions = self.shortcuts[km]
            actions[:] = [r for r in actions if r[1] != ctx or r[2] != name]

            if not actions:
                self.accel_group.disconnect_key(*km)

        for km, pr in self.generic_shortcuts.get(name, []):
            self._add_shortcut(km, ctx, name, -pr, True)

        for km, pr in keys:
            self._add_shortcut(km, ctx, name, -pr, False)

    def activate(self, _group, window, key, modifier):
        found_priority = 10000
        actions = []
        ctx_getter = self.make_context_getter(window)

        window.last_shortcut = key, modifier
        for pr, ctx, name, _ in self.shortcuts[(key, modifier)]:
            if pr > found_priority:
                break

            ctx_obj = ctx_getter(ctx)
            if ctx_obj is not None:
                try:
                    action = self.actions[ctx][name]
                except KeyError:
                    if name[0] == '!':
                        dname, _, param = name.partition('/')
                        dmenu = self.actions[ctx][dname]
                        action = dmenu.resolve(*(ctx_obj + (param,)))
                        if not action:
                            continue
                    else:
                        raise KeyError('%s %s' % (ctx, name))

                actions.append(action)
                if pr < found_priority:
                    found_priority = pr

        if actions:
            if len(actions) == 1:
                result = action(ctx_getter)
                return result is None or result
            else:
                show_dups_menu(actions, window, self, ctx_getter)

        return False

    def activate_menu_item(self, item):
        item.get_parent().tr_window.last_shortcut = None, None
        item.entry(item.ctx_getter)

    def on_menu_key_press(self, menu, event):
        if event.keyval == F2:
            item = getattr(menu, 'current_item', None)
            if item:
                w = ShortcutChangeDialog(self, item.entry.ctx, item.entry.name)
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

    def make_context_getter(self, window):
        cache = self.get_context_cache(window)
        def ctx_getter(ctx):
            return self._find_context(ctx, cache)

        return ctx_getter

    def get_km_for_action(self, ctx, name):
        result = []
        for km, actions in self.shortcuts.iteritems():
            for pr, actx, aname, is_generic in actions:
                if ctx == actx and name == aname:
                    result.append((km, pr, is_generic))

        return result

    def add_context(self, ctx, depends, callback):
        if isinstance(depends, str):
            depends = (depends,)
        self.contexts[ctx] = depends, callback


def on_item_select(item, is_select):
    item.get_parent().current_item = item if is_select else None

def fill_menu(menu, window, activator, ctx_getter, actions):
    menu.set_reserve_toggle_size(False)
    menu.tr_window = window

    def activate_sub_menu(item, entry):
        menu = item.get_submenu()
        if not getattr(menu, 'already_filled', None):
            fill_menu(menu, window, activator, ctx_getter, entry.get_entries(ctx_getter))
            menu.already_filled = True

    for entry in actions:
        km = activator.get_km_for_action(entry.ctx, entry.name)
        item = entry.get_widget(ctx_getter, km)
        if isinstance(entry, MenuEntry):
            item.set_submenu(gtk.Menu())
            item.connect('activate', activate_sub_menu, entry)
        else:
            item.connect('activate', activator.activate_menu_item)

        #item.contains_all_run_data = ard

        #item.activate_context = acontext
        item.connect_after('select', on_item_select, True)
        item.connect_after('deselect', on_item_select, False)
        item.entry = entry
        item.ctx_getter = ctx_getter
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
        ctx_getter = activator.make_context_getter(window)
        actions = activator.menu.get_entry_for_path(path).get_entries(ctx_getter)

        menu = gtk.Menu()
        fill_menu(menu, window, activator, ctx_getter, actions)
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

    def on_accel_edited(self, _renderer, path, key, mod, _code, model):
        model[path][0] = key
        model[path][1] = mod
        self.add_rows_if_needed(model)

    def on_accel_cleared(self, _renderer, path, model):
        if model[path][0] == model[path][1] == 0:
            model[path][0], model[path][1] = gtk.accelerator_parse('BackSpace')
        else:
            model[path][0] = 0
            model[path][1] = 0

        self.add_rows_if_needed(model)

    def on_priority_edited(_self, _renderer, path, text, model):
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

    def on_key_press_event(self, _window, event):
        if event.keyval == Escape:
            self.quit()
            self.destroy()
            return True

        return False
