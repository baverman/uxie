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


class InputDialog(gtk.Dialog):
    def __init__(self, title=None, parent=None, flags=0, buttons=None):
        if flags is None:
            flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT

        if buttons is None:
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                gtk.STOCK_OK, gtk.RESPONSE_ACCEPT)

        gtk.Dialog.__init__(self, title, parent, flags, buttons)
        self.set_default_response(gtk.RESPONSE_ACCEPT)

        self.entry = gtk.Entry()
        self.entry.set_activates_default(True)
        self.vbox.pack_start(self.entry)
        self.entry.show()
