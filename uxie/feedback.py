import weakref
import gtk
import glib

from .misc import FlatBox

def timeout(feedback):
    feedback = feedback()
    if feedback and feedback.is_active():
        feedback.cancel()

    return False


class FeedbackManager(object):
    def __init__(self):
        self.feedbacks = weakref.WeakKeyDictionary()

    def add_feedback(self, window, feedback):
        self.feedbacks.setdefault(window, []).append(feedback)
        self.arrange(window)
        return feedback

    def arrange(self, window):
        feedbacks = self.feedbacks[window][:] = sorted([
            r for r in self.feedbacks[window] if r.is_active()])

        win = window.window
        _, _, x, y, _ = win.get_geometry()

        for f in feedbacks:
            mw, mh = f.get_size()
            f.show(win, x - mw, y - mh)
            y -= mh + 2


class FeedbackHelper(object):
    def __init__(self, fm, window):
        self.window = window
        self.fm = fm

    def show(self, text, category=None, timeout=None):
        return self.fm.add_feedback(self.window, TextFeedback(text, category, timeout))

    def show_widget(self, widget, priority=0, timeout=0):
        return self.fm.add_feedback(self.window, WidgetFeedback(widget, priority, timeout))


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

    def show(self, window, x, y):
        if self.window.window.get_parent() != window:
            self.window.window.reparent(window, 0, 0)

        if not self.window.get_visible() and self.timeout > 0:
            glib.timeout_add(self.timeout, timeout, weakref.ref(self))

        self.window.move(x, y)
        self.window.show()

    def cancel(self):
        self.window.destroy()
        self.window = None

    def is_active(self):
        return self.window is not None


class WidgetFeedback(Feedback):
    def __init__(self, widget, priority=0, timeout=0):
        self.priority = priority
        self.timeout = timeout

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

    def __init__(self, text, category=None, timeout=None):
        category = category or 'info'

        if timeout is None:
            timeout = max(1500, 500 + len(text)*100)

        box = gtk.HBox()
        box.pack_start(FlatBox(5, TextFeedback.COLORS[category]), False, True)

        label = gtk.Label(text)
        label.set_padding(7, 5)
        box.pack_start(label, True, True)

        WidgetFeedback.__init__(self, box, 0, timeout)