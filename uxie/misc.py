import gtk

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


class BuilderAware(object):
    def __init__(self, glade_file):
        self.gtk_builder = gtk.Builder()
        self.gtk_builder.add_from_file(glade_file)
        self.gtk_builder.connect_signals(self)

    def __getattr__(self, name):
        obj = self.gtk_builder.get_object(name)
        if not obj:
            raise AttributeError('Builder have no %s object' % name)

        setattr(self, name, obj)
        return obj