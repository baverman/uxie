import gtk
from time import time

from .utils import send_focus_change, refresh_gui, idle

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

        self.key_press_handler_id = None
        self.focus_out_handler_id = None

    def on_key_press_event(self, widget, event):
        keymap = gtk.gdk.keymap_get_default()
        keyval, _, _, mask = keymap.translate_keyboard_state(
            event.hardware_keycode, event.state, event.group)
        t = gtk.gdk.keyval_to_unicode(keyval)

        if keyval == gtk.keysyms.Escape:
            self.popdown(widget)
            return True

        if (t and event.state | mask == mask) or keyval == gtk.keysyms.BackSpace:
            return False
        else:
            self.view.event(event)
            return True

    def popup(self, widget):
        self.set_position(widget)
        self.show()
        send_focus_change(self.view, True)

        if not self.key_press_handler_id:
            self.key_press_handler_id = widget.connect('key-press-event', self.on_key_press_event)

        if not self.focus_out_handler_id:
            self.focus_out_handler_id = widget.get_toplevel().connect(
                'focus-out-event', self.on_main_window_focus_out, widget)

    def on_main_window_focus_out(self, window, event, widget):
        self.popdown(widget)

    def popdown(self, widget):
        widget.handler_disconnect(self.key_press_handler_id)
        self.key_press_handler_id = None

        widget.get_toplevel().handler_disconnect(self.focus_out_handler_id)
        self.focus_out_handler_id = None

        send_focus_change(self.view, False)
        self.hide()

    def is_stop(self):
        obj = self.fill_object = object()

        t = time()
        while True:
            if time() - t > 0.1:
                refresh_gui()
                if obj is not self.fill_object:
                    return

                t = time()

            yield True

    def on_row_activated(self, view, path, column, widget):
        self.popdown(widget)
        widget.handler_block(widget.on_changed_handler_id)
        try:
            widget.completer_activate_cb(view, path, widget, True)
        finally:
            widget.handler_unblock(widget.on_changed_handler_id)

    def on_cursor_changed(self, view, widget):
        widget.handler_block(widget.on_changed_handler_id)
        try:
            widget.completer_activate_cb(view, view.get_cursor()[0], widget, False)
        finally:
            widget.handler_unblock(widget.on_changed_handler_id)


class EntryCompleter(Completer):

    def set_position(self, entry):
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
        idle(entry.completer_fill_cb, self.view, entry, self.is_stop())

        if not self.get_visible():
            idle(self.popup, entry)

    def attach(self, entry, fill_cb, activate_cb):
        entry.completer_fill_cb = fill_cb
        entry.on_changed_handler_id = entry.connect('changed', self.on_entry_changed)

        entry.completer_activate_cb = activate_cb
        self.view.connect('row-activated', self.on_row_activated, entry)
        self.view.connect('cursor-changed', self.on_cursor_changed, entry)


def create_simple_complete_view():
    model = gtk.ListStore(str)
    view = gtk.TreeView(model)
    view.set_headers_visible(False)
    view.append_column(gtk.TreeViewColumn('title', gtk.CellRendererText(), text=0))
    return view