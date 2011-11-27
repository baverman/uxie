import gtk
from time import time
from contextlib import contextmanager

from .utils import send_focus_change, refresh_gui, idle

ACTIVATE_ROW_KEYS = set((gtk.keysyms.Return, gtk.keysyms.ISO_Enter, gtk.keysyms.KP_Enter))

class Completer(gtk.Window):
    def __init__(self, view):
        gtk.Window.__init__(self, gtk.WINDOW_POPUP)
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_POPUP_MENU)
        self.set_resizable(False)

        self.sw = gtk.ScrolledWindow()
        self.add(self.sw)
        self.sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.sw.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        self.view = view
        self.sw.add(view)

        self.sw.show_all()

        self.complete_on_printable_chars = False
        self.pass_enter_key = False

        self.active = False

    def request_fill(self, widget, check, args):
        try:
            widget.completer_fill_cb(self.view, widget, check, *args)
        except StopIteration:
            pass
        else:
            if len(self.view.get_model()):
                if self.active:
                    self.set_position(widget)
                else:
                    self.popup(widget)

                self.view.window.freeze_updates()
                self.view.set_cursor((0,))
                self.view.get_selection().unselect_all()
                self.view.window.thaw_updates()
            else:
                self.popdown(widget)

    def complete(self, widget, *args):
        idle(self.request_fill, widget, self.is_stop(widget), args)

    def on_key_press_event(self, widget, event):
        keymap = gtk.gdk.keymap_get_default()
        keyval, _, _, mask = keymap.translate_keyboard_state(
            event.hardware_keycode, event.state, event.group)
        t = gtk.gdk.keyval_to_unicode(keyval)

        if keyval == gtk.keysyms.Escape:
            self.popdown(widget)
            return True

        if (t and event.state | mask == mask) or keyval == gtk.keysyms.BackSpace:
            if self.complete_on_printable_chars:
                self.complete(widget)
            return False
        elif keyval in ACTIVATE_ROW_KEYS:
            path, column = self.view.get_cursor()
            if path and self.view.get_selection().path_is_selected(path):
                self.on_row_activated(self.view, path, column, widget)
            elif self.pass_enter_key:
                self.popdown(widget)
                return False

            return True
        else:
            self.view.event(event)
            return True

    def popup(self, widget):
        if self.active:
            return

        self.active = True
        self.set_position(widget)
        self.show()
        send_focus_change(self.view, True)

        self.cursor_changed_handler_id = self.view.connect('cursor-changed',
            self.on_cursor_changed, widget)

        #self.move_cursor_handler_id = self.view.connect('move-cursor',
        #    self.on_move_cursor, widget)

        self.key_press_handler_id = widget.connect('key-press-event', self.on_key_press_event)

        self.focus_out_handler_id = widget.get_toplevel().connect(
            'focus-out-event', self.on_main_window_focus_out, widget)

    def on_main_window_focus_out(self, window, event, widget):
        self.popdown(widget)

    def popdown(self, widget):
        if not self.active:
            return

        self.active = False
        widget.handler_disconnect(self.key_press_handler_id)
        widget.get_toplevel().handler_disconnect(self.focus_out_handler_id)
        self.view.handler_disconnect(self.cursor_changed_handler_id)
        #self.view.handler_disconnect(self.move_cursor_handler_id)

        send_focus_change(self.view, False)
        self.hide()

    def is_stop(self, widget):
        obj = self.fill_object = object()

        t = time()
        while True:
            if time() - t > 0.1:
                refresh_gui()
                if obj is not self.fill_object:
                    return

                if not self.active and len(self.view.get_model()):
                    self.popup(widget)

                t = time()

            yield True

    @contextmanager
    def block_changed_handler(self, widget):
        if getattr(widget, 'on_changed_handler_id', None):
            widget.handler_block(widget.on_changed_handler_id)

        try:
            yield
        finally:
            if getattr(widget, 'on_changed_handler_id', None):
                widget.handler_unblock(widget.on_changed_handler_id)

    def on_row_activated(self, view, path, column, widget):
        self.popdown(widget)
        with self.block_changed_handler(widget):
            widget.completer_activate_cb(view, path, widget, True)

    def on_cursor_changed(self, view, widget):
        with self.block_changed_handler(widget):
            widget.completer_activate_cb(view, view.get_cursor()[0], widget, False)

    def on_move_cursor(self, view, step, count, widget):
        return False
        if step == gtk.MOVEMENT_DISPLAY_LINES and not view.get_cursor()[0]:
            if step > 0:
                path = (0,)
            else:
                path = (len(view.get_model()),)

            print path
            view.set_cursor(path)
            return True

    def attach(self, textview, fill_cb, activate_cb):
        textview.completer_fill_cb = fill_cb
        textview.completer_activate_cb = activate_cb


class EntryCompleter(Completer):
    def set_position(self, entry):
        if not self.active:
            return

        self.view.columns_autosize()
        self.set_transient_for(entry.get_toplevel())

        x, y = entry.window.get_origin()
        w, h = self.view.size_request()
        _, eh = entry.size_request()

        screen = entry.get_screen()
        monitor_num = screen.get_monitor_at_window(entry.window)
        sg = screen.get_monitor_geometry(monitor_num)

        h = min(h, sg.height / 3) + 5
        self.sw.set_size_request(-1 if w > 100 else 100, h)

        pw, ph = self.size_request()
        if x + pw > sg.x + sg.width:
            x = sg.x + sg.width - pw

        if y + ph + eh <= sg.y + sg.height:
            y += eh
        else:
            y -= ph

        self.move(x, y)
        self.resize(*self.size_request())

    def on_entry_changed(self, entry, *args):
        self.complete(entry, *args)

    def attach(self, entry, fill_cb, activate_cb):
        Completer.attach(self, entry, fill_cb, activate_cb)
        entry.on_changed_handler_id = entry.connect('changed', self.on_entry_changed)


class TextViewCompleter(Completer):
    def __init__(self, view):
        Completer.__init__(self, view)
        self.complete_on_printable_chars = True

    def set_position(self, textview):
        if not self.active:
            return

        self.view.columns_autosize()
        self.set_transient_for(textview.get_toplevel())

        buf = textview.get_buffer()
        cursor_rect = textview.get_iter_location(buf.get_iter_at_mark(buf.get_insert()))

        x, y = textview.buffer_to_window_coords(gtk.TEXT_WINDOW_WIDGET, cursor_rect.x, cursor_rect.y)
        ew = cursor_rect.width
        eh = cursor_rect.height

        ox, oy = textview.window.get_origin()
        x += ox
        y += oy

        w, h = self.view.size_request()

        screen = textview.get_screen()
        monitor_num = screen.get_monitor_at_window(textview.window)
        sg = screen.get_monitor_geometry(monitor_num)

        h = min(h, sg.height / 3) + 5
        self.sw.set_size_request(-1 if w > 100 else 100, h)

        pw, ph = self.size_request()
        if x + pw > sg.x + sg.width:
            x = sg.x + sg.width - pw - ew

        if y + ph + eh <= sg.y + sg.height:
            y += eh
        else:
            y -= ph

        self.move(x, y)
        self.resize(*self.size_request())

def create_simple_complete_view():
    model = gtk.ListStore(str)
    view = gtk.TreeView(model)
    view.set_headers_visible(False)
    view.append_column(gtk.TreeViewColumn('title', gtk.CellRendererText(), text=0))
    return view