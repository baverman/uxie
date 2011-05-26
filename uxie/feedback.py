import weakref
import gtk

from .misc import FlatBox


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


class WidgetFeedback(Feedback):
    def __init__(self, widget, priority=0):
        self.priority = priority

        self.window = self.create_window()
        widget.show_all()
        self.window.add(widget)
        self.window.realize()


class TextFeedback(WidgetFeedback):
    COLORS = {
        'info': '#55C',
        'done': '#5C5',
        'warn': '#CC5',
        'error': '#C55',
    }

    def __init__(self, text, category='info'):
        box = gtk.HBox()
        box.pack_start(FlatBox(5, TextFeedback.COLORS[category]), False, True)

        label = gtk.Label(text)
        label.set_padding(7, 5)
        box.pack_start(label, True, True)

        WidgetFeedback.__init__(self, box, 0)