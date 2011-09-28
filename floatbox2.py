import gtk
from uxie.floating import TextFeedback, Manager, Feedback
from uxie.utils import idle

w = gtk.Window(gtk.WINDOW_TOPLEVEL)
w.set_default_size(800, 500)
w.connect('delete-event', gtk.main_quit)


tv = gtk.TextView()
w.add(tv)

tv.get_buffer().set_text('text text')

w.show_all()

fmanager = Manager()

def debug_expose(widget):
    def inner(widget, event):
        print 'expose', widget, event

    widget.connect_after('expose-event', inner)


n = 0
nn = True
def on_btn_click(btn):
    global n, nn
    n += 1
    #nn = not nn
    fmanager.add(tv, TextFeedback('text%d' % n), timeout=6000, place_vertically=nn)

def do():
    btn = gtk.Button('Click')
    www = gtk.EventBox()
    www.add(btn)
    btn.connect('clicked', on_btn_click)
    fmanager.add(tv, Feedback(www))

idle(do)

gtk.main()