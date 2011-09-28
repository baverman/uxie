import gtk

from .utils import send_focus_change

class InteractiveSearch(object):
    def __init__(self, search_callback, widget_created_cb):
        self.floating = None
        self.widget = None
        self.entry = None
        self.search_callback = search_callback
        self.widget_created_cb = widget_created_cb

    def attach(self, widget):
        self.widget = widget
        self.widget.connect('key-press-event', self.on_key_press)

    def on_key_press(self, widget, event):
        state = event.state
        keyval = event.keyval

        t = gtk.gdk.keyval_to_unicode(keyval)
        is_active = self.is_active()
        printable_mask = ( state | gtk.gdk.SHIFT_MASK ) == gtk.gdk.SHIFT_MASK

        if (t and printable_mask) or (is_active and keyval == gtk.keysyms.BackSpace):
            self.delegate(event)
            return True

        if not is_active:
            return False

        if not state:
            if keyval == gtk.keysyms.Escape:
                self.floating.hide()
                return True

            if keyval == gtk.keysyms.Up:
                self.search_callback(self.entry.get_text(), -1, True)
                return True

            if keyval == gtk.keysyms.Down:
                self.search_callback(self.entry.get_text(), 1, True)
                return True

            if keyval == gtk.keysyms.Return:
                self.floating.hide()
                return False

        return True

    def on_entry_changed(self, entry):
        self.search_callback(entry.get_text(), 1, False)

    def ensure_window_created(self):
        if not self.floating:
            self.floating = gtk.EventBox()

            frame = gtk.Frame()
            frame.set_shadow_type(gtk.SHADOW_ETCHED_IN)
            self.floating.add(frame)

            self.entry = gtk.Entry()
            self.entry.connect('changed', self.on_entry_changed)
            frame.add(self.entry)

            self.widget_created_cb(self.floating)
            return False

        return True

    def is_active(self):
        return self.floating and self.floating.get_visible()

    def delegate(self, event):
        if not self.ensure_window_created() or not self.floating.get_visible():
            self.floating.show()
            self.entry.set_text('')
            send_focus_change(self.entry, True)

        self.entry.event(event)
