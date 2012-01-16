import time
import weakref
import gtk
import glib

from .misc import FlatBox

def floating_timeout(floating):
    floating = floating()
    if floating and floating.is_active():
        floating.cancel()

    return False


class Manager(object):
    def __init__(self):
        self.floatings = weakref.WeakKeyDictionary()

    def add(self, parent, floating, priority=None, timeout=None, place_vertically=True):
        if timeout:
            glib.timeout_add(timeout, floating_timeout, weakref.ref(floating))

        if priority is None:
            priority = 0

        floating.start = time.time()
        self.floatings.setdefault(parent, []).append(
            (-priority, floating.start, place_vertically, floating))
        self.arrange(parent)
        return floating

    def arrange(self, parent):
        floatings = self.floatings[parent][:] = [
            r for r in self.floatings[parent] if r[3].is_active()]

        vfloats = sorted([r for r in floatings if r[2]])
        hfloats = sorted([r for r in floatings if not r[2]])

        y = -1
        sx = -1
        for _, _, _, f in vfloats:
            if f.widget.get_parent():
                f.widget.float_pos = -1, y
                allocate_float(parent.allocation, f.widget)
            else:
                add_float(parent, f.widget, -1, y)

            mw, mh = f.get_size()
            if y == -1:
                sx -= mw + 5

            y -= mh + 2

        x = sx
        for _, _, _, f in hfloats:
            if f.widget.get_parent():
                f.widget.float_pos = x, -1
                allocate_float(parent.allocation, f.widget)
            else:
                add_float(parent, f.widget, x, -1)

            mw, mh = f.get_size()
            x -= mw + 5


class FeedbackHelper(object):
    def __init__(self, fm, parent):
        self.parent = parent
        self.fm = fm

    def show(self, text, category=None, timeout=None):
        fb = TextFeedback(text, category)
        timeout = timeout or fb.timeout
        return self.fm.add(self.parent, fb, timeout=timeout)

    def show_widget(self, widget, priority=None, timeout=None, place_vertically=True):
        return self.fm.add(self.parent, Feedback(widget), priority, timeout, place_vertically)


class Feedback(object):
    def __init__(self, widget):
        self.widget = widget
        self.cancel_cb = None

    def get_size(self):
        return self.widget.size_request()

    def cancel(self):
        if self.widget:
            if self.cancel_cb:
                self.cancel_cb(self)

            remove_float(self.widget)
            self.widget = None

    def is_active(self):
        return self.widget is not None

    def on_cancel(self, cancel_cb):
        self.cancel_cb = cancel_cb
        return self


class TextFeedback(Feedback):
    COLORS = {
        'info': '#55C',
        'done': '#5C5',
        'warn': '#CC5',
        'error': '#C55',
    }

    def __init__(self, text, category=None, markup=False):
        category = category or 'info'

        self.timeout = max(1500, 500 + len(text)*50)

        w = gtk.EventBox()

        frame = gtk.Frame()
        w.add(frame)

        box = gtk.HBox()
        frame.add(box)
        fb = FlatBox(5, TextFeedback.COLORS[category])
        box.pack_start(fb, False, True)

        if markup:
            label = gtk.Label()
            label.set_markup(text)
        else:
            label = gtk.Label(text)

        label.set_padding(7, 5)
        label.set_selectable(True)
        box.pack_start(label, True, True)
        self.label = label

        Feedback.__init__(self, w)


def allocate_float(allocation, widget):
    w, h = widget.size_request()
    x, y = widget.float_pos

    if x is None:
        x = (allocation.width - w) / 2
    elif x < 0:
        x = allocation.width - w + x

    if y is None:
        y = (allocation.height - h) / 2
    elif y < 0:
        y = allocation.height - h + y

    calloc = gtk.gdk.Rectangle(x, y, w, h)
    widget.size_allocate(calloc)

def remove_float(widget, destroy=True):
    p = widget.get_parent()
    if p:
        p.handler_disconnect(widget.size_allocate_handler_id)
        widget.unparent()

    if destroy:
        widget.destroy()

def float_state_changed(widget, event):
    if event.state != gtk.gdk.VISIBILITY_UNOBSCURED:
        widget.window.show()

    return False

def on_parent_destroy(parent, widget):
    widget.unparent()

def add_float(parent, widget, x=None, y=None):
    widget.show_all()
    widget.set_parent(parent)

    widget.realize()

    widget.float_pos = x, y
    allocate_float(parent.allocation, widget)

    widget.size_allocate_handler_id = parent.connect_after('size-allocate',
        lambda w, event: allocate_float(w.allocation, widget))

    parent.connect('destroy', on_parent_destroy, widget)

    widget.connect('visibility-notify-event', float_state_changed)
