import gtk

from uxie.data.grid import Grid, RowRenderer, TextColumn

w = gtk.Window(gtk.WINDOW_TOPLEVEL)
w.set_default_size(500, 500)
w.connect('delete-event', gtk.main_quit)

sw = gtk.ScrolledWindow()
sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
w.add(sw)

model = [{'id':i, 'name':'name%d' % i, 'desc': 'description %d' % i } for i in xrange(100)]

renderer = RowRenderer()
renderer.add_column(TextColumn('id'), pixels=30)
renderer.add_column(TextColumn('name'), percents=30, chars=10)
renderer.add_column(TextColumn('desc'), percents=70, chars=20)

grid = Grid()
grid.renderer = renderer
grid.model = model
sw.add(grid)
grid.set_cursor(0, 0)

w.show_all()

gtk.main()