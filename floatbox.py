import gtk

from uxie.floating import FloatBox, TextFeedback
from uxie.utils import idle

w = gtk.Window(gtk.WINDOW_TOPLEVEL)
w.set_default_size(800, 500)
w.connect('delete-event', gtk.main_quit)


hp = gtk.HPaned()
hp.props.position = 400
w.add(hp)

hv1 = gtk.VPaned()
hv1.props.position = 250
hp.add1(hv1)

hv2 = gtk.VPaned()
hv2.props.position = 250
hp.add2(hv2)

views = []
fboxes = []
for p in [hv1, hv2]:
    for add in [p.add1, p.add2]:
        #v = gtk.TextView()
        fb = FloatBox()
        f = gtk.Frame()
        #f.add(v)
        fb.add(f)
        add(fb)
        #views.append(v)
        fboxes.append(fb)

#for i, v in enumerate(views):
#    v.get_buffer().set_text('view%s' % i)

w.show_all()

def do():
    msg = TextFeedback('Wow', timeout=0)
    fboxes[0].add(msg.widget, -1, -1)
    msg.widget.show_all()
    #msg.widget.queue_draw()
    #fboxes[0].queue_draw()

idle(do)

gtk.main()