import time
import weakref
import gtk
import glib

from .misc import FlatBox

def timeout(floating):
    floating = floating()
    if floating and floating.is_active():
        floating.cancel()

    return False


class Manager(object):
    def __init__(self):
        self.floatings = {}

    def add(self, window, floating):
        top = window.get_toplevel()
        print 'before', self.floatings.get(top, None)
        self.floatings.setdefault(top, []).append((floating, window))
        print 'after', self.floatings[top]
        self.arrange(top)
        return floating

    def arrange(self, window):
        floatings = self.floatings[window][:] = sorted([
            r for r in self.floatings[window] if r[0].is_active()])
        print 'arr', floatings, self.floatings[window]

        _, _, x, y, _ = window.get_geometry()

        for f, fwindow in floatings:
            if not fwindow.is_viewable():
                print 'not vu', fwindow
                continue
            #print window, fwindow, fwindow.get_origin()
            mw, mh = f.get_size()
            f.show(fwindow, x - mw, y - mh)
            y -= mh + 2


class FeedbackHelper(object):
    def __init__(self, fm, window):
        self.window = window
        self.fm = fm

    def show(self, text, category=None, timeout=None):
        return self.fm.add_feedback(self.window, TextFeedback(text, category, timeout))

    def show_widget(self, widget, priority=0, timeout=0):
        return self.fm.add_feedback(self.window, Feedback(widget, priority, timeout))


class Feedback(object):
    def __init__(self, widget, priority=0, timeout=0):
        self.priority = priority
        self.timeout = timeout
        self.widget = widget

    def __cmp__(self, other):
        if self.priority < other.priority:
            return 1
        elif self.priority > other.priority:
            return -1
        else:
            return 0

    def get_size(self):
        return self.widget.size_request()

    def show(self, window, x, y):
        if not self.window.get_visible() and self.timeout > 0:
            glib.timeout_add(self.timeout, timeout, weakref.ref(self))
            self.start = time.time()

        self.window.move(x, y)
        self.window.show()

    def cancel(self):
        if self.window:
            self.window.destroy()
            self.window = None

    def is_active(self):
        return self.window is not None


class TextFeedback(Feedback):
    COLORS = {
        'info': '#55C',
        'done': '#5C5',
        'warn': '#CC5',
        'error': '#C55',
    }

    def __init__(self, text, category=None, timeout=None):
        category = category or 'info'

        if timeout is None:
            timeout = max(1500, 500 + len(text)*50)

        frame = gtk.Frame()
        box = gtk.HBox()
        frame.add(box)
        box.pack_start(FlatBox(5, TextFeedback.COLORS[category]), False, True)

        label = gtk.Label(text)
        label.set_padding(7, 5)
        box.pack_start(label, True, True)

        Feedback.__init__(self, frame, 0, timeout)


class FloatBox(gtk.Container):
    __gsignals__ = {
        'size-request': 'override',
        'size-allocate': 'override',
    }

    def __init__(self):
        gtk.Container.__init__(self)
        self.set_has_window(False)
        self.child = None
        self.floats = {}

    def add(self, widget, x=0, y=0):
        if not self.child:
            self.child = widget
            widget.set_parent(self)
        else:
            self.floats[widget] = x, y
            widget.set_parent(self)
            widget.realize()

    def do_remove(self, widget):
        widget.unparent()
        if widget is self.child:
            self.child = None
        else:
            del self.floats[widget]

    def move(self, widget, x, y):
        self.floats[widget] = (x, y)

    def do_size_request(self, req):
        if self.child:
            w, h = self.child.size_request()
            req.width = w
            req.height = h

    def do_size_allocate(self, allocation):
        self.allocation = allocation
        if self.child:
            self.child.size_allocate(allocation)

            for f, (x, y) in self.floats.iteritems():
                w, h = f.size_request()
                if x < 0:
                    x = allocation.x + allocation.width - w + x
                else:
                    x = allocation.x + x

                if y < 0:
                    y = allocation.y + allocation.height - h + y
                else:
                    y = allocation.y + y

                calloc = gtk.gdk.Rectangle(x, y, w, h)
                f.size_allocate(calloc)

    def do_forall(self, int, callback, data):
        if self.child:
            callback(self.child, data)
            for f in list(self.floats):
                print f, callback
                callback(f, data)
