import weakref
import gtk

class FeedbackManager(object):
    def __init__(self):
        self.feedbacks = weakref.WeakKeyDictionary()

    def add_feedback(self, window, feedback, timeout=-1):
        self.feedbacks.setdefault(window, []).append(feedback)
        self.arrange(window)

    def arrange(self, window):
        feedbacks = sorted(self.feedbacks[window])

        win = window.window
        x, y, w, h, _ = win.get_geometry()
        x, y = win.get_origin()

        y = y + h
        for f in feedbacks:
            mw, mh = f.get_size()
            f.window.move(x + w - mw, y - mh)
            f.window.show()

            y -= mh + 2


class Feedback(object):
    def __cmp__(self, other):
        if self.priority < other.priority:
            return 1
        elif self.priority > other.priority:
            return -1
        else:
            return 0

    def create_window(self):
        window = gtk.Window(gtk.WINDOW_POPUP)
        window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_TOOLTIP)
        window.set_can_focus(False)

        return window

    def get_size(self):
        self.window.resize(*self.window.size_request())
        return self.window.get_size()


class TextFeedback(Feedback):
    COLORS = {
        'info': '#55C',
        'done': '#5C5',
        'warn': '#CC5',
        'error': '#C55',
    }

    def __init__(self, text, category='info'):
        self.priority = 0

        self.window = self.create_window()

        box = gtk.HBox()
        self.window.add(box)

        box.pack_start(FlatBox(5, TextFeedback.COLORS[category]), False, True)

        label = gtk.Label(text)
        label.set_padding(7, 5)
        box.pack_start(label, True, True)

        box.show_all()

        self.window.realize()


class FlatBox(gtk.DrawingArea):
    __gsignals__ = {
        'size-request': 'override',
        'realize': 'override',
        'expose-event': 'override',
    }

    def __init__(self, width, color):
        gtk.DrawingArea.__init__(self)
        self.width = width
        self.color = color

    def do_size_request(self, req):
        req.width = req.height = self.width

    def do_expose_event(self, event):
        return True

    def do_realize(self):
        gtk.DrawingArea.do_realize(self)
        self.window.set_background(self.get_colormap().alloc_color(self.color))
