import gtk

from uxie.floating import FloatBox

w = gtk.Window(gtk.WINDOW_TOPLEVEL)
w.set_default_size(400, 400)
w.connect('delete-event', gtk.main_quit)

fb = FloatBox()
w.add(fb)

tv = gtk.TextView()
fb.add(tv)

e = gtk.Entry()
fb.add(e)
fb.move(e, 100, 100)

w.show_all()

gtk.main()