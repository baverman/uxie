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

    def add(self, parent, floating, priority=0, timeout=0, place_vertically=True):
        if timeout:
            glib.timeout_add(timeout, floating_timeout, weakref.ref(floating))

        floating.start = time.time()
        self.floatings.setdefault(parent, []).append(
            (priority, floating.start, place_vertically, floating))
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
        return self.fm.add(self.parent, fb , 5, timeout)

    def show_widget(self, widget, priority=0, timeout=None, place_vertically=True):
        return self.fm.add(self.parent, Feedback(widget), priority, timeout, place_vertically)


class Feedback(object):
    def __init__(self, widget):
        self.widget = widget

    def get_size(self):
        return self.widget.size_request()

    def cancel(self):
        if self.widget:
            remove_float(self.widget)
            self.widget = None

    def is_active(self):
        return self.widget is not None


class TextFeedback(Feedback):
    COLORS = {
        'info': '#55C',
        'done': '#5C5',
        'warn': '#CC5',
        'error': '#C55',
    }

    def __init__(self, text, category=None):
        category = category or 'info'

        self.timeout = max(1500, 500 + len(text)*50)

        w = gtk.EventBox()

        frame = gtk.Frame()
        w.add(frame)

        box = gtk.HBox()
        frame.add(box)
        fb = FlatBox(5, TextFeedback.COLORS[category])
        box.pack_start(fb, False, True)

        label = gtk.Label(text)
        label.set_padding(7, 5)
        box.pack_start(label, True, True)

        Feedback.__init__(self, w)


def allocate_float(allocation, widget):
    w, h = widget.size_request()
    x, y = widget.float_pos
    if x < 0:
        x = allocation.width - w + x

    if y < 0:
        y = allocation.height - h + y

    calloc = gtk.gdk.Rectangle(x, y, w, h)
    widget.size_allocate(calloc)

def remove_float(widget, destroy=True):
    p = widget.get_parent()
    p.handler_disconnect(widget.size_allocate_handler_id)
    widget.unparent()

    if destroy:
        widget.destroy()

def add_float(parent, widget, x=0, y=0):
    widget.show_all()
    widget.set_parent(parent)
    widget.realize()

    widget.float_pos = x, y
    allocate_float(parent.allocation, widget)

    widget.size_allocate_handler_id = parent.connect_after('size-allocate',
        lambda w, event: allocate_float(w.allocation, widget))