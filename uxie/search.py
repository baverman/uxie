import gtk

from .utils import send_focus_change

class InteractiveSearch(object):
    def __init__(self):
        self.window = None
        self.widget = None
        self.entry = None

    def attach(self, widget):
        self.widget = widget
        self.widget.connect('key-press-event', self.on_key_press)

    def on_key_press(self, widget, event):
        t = gtk.gdk.keyval_to_unicode(event.keyval)
        if t or event.keyval == gtk.keysyms.BackSpace:
            self.delegate(event)
            return True

        if event.keyval == gtk.keysyms.Escape:
            self.window.hide()
            return True

        if event.keyval == gtk.keysyms.Return:
            self.window.hide()

        return False

    def ensure_window_created(self):
        top = self.widget.get_toplevel()
        if not self.window:
            self.window = gtk.Window(gtk.WINDOW_POPUP)
            self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_UTILITY)
            self.window.set_border_width(3)

            frame = gtk.Frame()
            frame.set_shadow_type(gtk.SHADOW_ETCHED_IN)
            self.window.add(frame)
            frame.show()

            self.entry = gtk.Entry()
            frame.add(self.entry)
            self.entry.show()
            self.entry.realize()

        if top.has_group():
            top.get_group().add_window(self.window)
        elif self.window.has_group():
            self.window.get_group().remove_window(self.window)

        self.window.set_screen(top.get_screen())

    def is_active(self):
        self.ensure_window_created()
        return self.window.get_visible()

    def delegate(self, event):
        self.ensure_window_created()
        if not self.window.get_visible():
            win = self.widget.window
            x, y, w, h, _ = win.get_geometry()
            x, y = win.get_origin()
            mw, mh = self.window.get_size()

            self.entry.set_text('')

            self.window.move(x + w - mw, y + h - mh)
            self.window.show()

            send_focus_change(self.entry, True)

        self.entry.event(event)
