import gtk
import gobject

class RowRenderer(object):
    def __init__(self):
        self.columns = []
        self.widths = []
        self.max_width = 0
        self.width = None
        self.height = None
        self.last_max_width = None
        self.minimal_column_width = 10
        self.calculated_widths = {}

    def add_column(self, column, pixels=None, percents=None, chars=None):
        self.columns.append(column)
        self.widths.append((pixels if chars is None else chars*10, percents))

    def draw(self, row, x, y, window, widget, earea, flags):
        for i, r in enumerate(self.renderers):
            c = self.columns[i]
            w = self.calculated_widths[i]
            c.set_attributes(r, row)

            rect = (x, y, w, self.height,)
            r.render(window, widget, rect, rect, earea, flags)

            x += w
            x += 1

    def get_size(self):
        return self.width, self.height

    def set_max_width(self, widget, max_width):
        try:
            self.renderers
        except:
            self.renderers = []
            for c in self.columns:
                self.renderers.append(c.get_renderer())

        if self.height is None:
            self.height = max(r.get_size(widget)[3] for r in self.renderers)

        if self.last_max_width != max_width or max_width < 0:
            fixed_width = 0
            self.calculated_widths.clear()
            for i, (pi, pr) in enumerate(self.widths):
                if pr is None:
                    fixed_width += pi
                    self.calculated_widths[i] = pi

            remain = max_width - fixed_width - len(self.widths) + 1
            for i, (pi, pr) in enumerate(self.widths):
                if pr is not None:
                    if pi is None:
                        pi = self.minimal_column_width

                    self.calculated_widths[i] = max(remain*pr/100, pi)

            self.width = sum(self.calculated_widths.values())

            if max_width >= 0:
                self.last_max_width = max_width


class Column(object):
    def get_renderer(self):
        r = gtk.CellRendererText()
        r.props.ypad = 4
        r.props.xpad = 5
        return r

    def set_attributes(self, renderer, row):
        renderer.props.text = self.to_string(row)

class TextColumn(Column):
    def __init__(self, name):
        self.name = name

    def to_string(self, row):
        return str(row[self.name])


class Grid(gtk.EventBox):
    __gsignals__ = {
        "expose-event": "override",
        "realize": "override",
        "size-request": "override",
        "size-allocate": "override",
        "key-press-event": "override",
        "set-scroll-adjustments": (
            gobject.SIGNAL_RUN_LAST | gobject.SIGNAL_ACTION,
            gobject.TYPE_NONE, (gtk.Adjustment, gtk.Adjustment)
        ),
    }

    def __init__(self):
        gtk.EventBox.__init__(self)
        self.set_has_window(True)
        self.set_set_scroll_adjustments_signal("set-scroll-adjustments")

        self.model = None
        self.renderer = None

    def do_size_request(self, req):
        req.width = 500
        req.height = 500
        if self.renderer:
            self.renderer.set_max_width(self, -1)
            req.width, h = self.renderer.get_size()

            if self.model:
                cnt = len(self.model)
                req.height = cnt*h + cnt - 1

    def refresh_scrolls(self):
        self.renderer.set_max_width(self, self.allocation.width)
        w, h = self.renderer.get_size()
        cnt = len(self.model)
        vcnt = self.allocation.height / (h + 1)

        self._vadj.configure(min(self._vadj.value, cnt), 0, cnt, 1.0, vcnt, vcnt)

        self._hadj.configure(min(self._hadj.value, w), 0, w,
            self.allocation.width*0.1, self.allocation.width*0.9, self.allocation.width)

    def do_size_allocate(self, allocation):
        self.allocation = allocation
        if self.window:
            self.window.move_resize(*allocation)

        self.refresh_scrolls()

    def do_set_scroll_adjustments(self, h_adjustment, v_adjustment):
        if h_adjustment:
            self._hscroll_handler_id = h_adjustment.connect(
                "value-changed", self.scroll_value_changed)
            self._hadj = h_adjustment

        if v_adjustment:
            self._vscroll_handler_id = v_adjustment.connect(
                "value-changed", self.scroll_value_changed)
            self._vadj = v_adjustment

    def do_expose_event(self, event):
        if self.window:
            rw, rh = self.renderer.get_size()

            cr = self.window.cairo_create()
            cr.set_source_rgb(0.8, 0.8, 0.8)
            cr.set_line_width(1.0)
            cr.set_dash([5.0, 2.0])

            y = 0
            x = -int(self._hadj.value)
            maxy = self.allocation.height
            i = int(self._vadj.value)
            while y < maxy:
                try:
                    row = self.model[i]
                except IndexError:
                    break

                self.renderer.draw(row, x, y, self.window, self, event.area, 0)
                y += rh
                i += 1

                cr.move_to(x, y + 0.5)
                cr.line_to(event.area.width, y + 0.5)
                cr.stroke()
                y += 1

            y -= 1
            x += 0.5
            for i in range(len(self.renderer.widths) - 1):
                x += self.renderer.calculated_widths[i] + 1
                cr.move_to(x, 0)
                cr.line_to(x, y)
                cr.stroke()

        return True

    def scroll_value_changed(self, *args):
        self.queue_draw()

    def do_realize(self):
        gtk.EventBox.do_realize(self)
        self.window.set_background(self.style.base[gtk.STATE_NORMAL])
