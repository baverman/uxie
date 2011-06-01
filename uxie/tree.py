from bisect import bisect
import gtk, gobject

class SelectionListStore(gtk.ListStore):
    __gsignals__ = {
        'row-deleted': 'override',
        'selection-changed': (
            gobject.SIGNAL_RUN_LAST | gobject.SIGNAL_ACTION,
            gobject.TYPE_NONE, (object,)
        ),
    }

    def __init__(self, *args):
        gtk.ListStore.__init__(self, *args)
        self.selection = {}
        self.ordered_selection = []
        self.selected_all = False

    def is_selected(self, path):
        return path in self.selection

    def is_selected_all(self, path):
        return self.selected_all

    def invert_selection(self, path):
        if path in self.selection:
            self.unselect(path)
        else:
            self.select(path)

    def select(self, path):
        if path in self.selection:
            return

        idx = bisect(self.ordered_selection, path)
        self.ordered_selection.insert(idx, path)
        self.selection[path] = True

        self.emit('selection-changed', self.selection)

    def unselect(self, path):
        if path not in self.selection:
            return

        del self.selection[path]
        self.ordered_selection.remove(path)
        self.selected_all = False

        self.emit('selection-changed', self.selection)

    def select_all(self):
        self.selected_all = True
        for r in self:
            self.selection[r.path] = True

        self.ordered_selection[:] = list(sorted(self.selection))

        self.emit('selection-changed', self.selection)

    def clear_selection(self):
        self.selected_all = False
        self.selection.clear()
        self.ordered_selection[:] = []

        self.emit('selection-changed', self.selection)

    def do_row_deleted(self, path):
        if not self.selection:
            return

        self.unselect(path)
        idx = bisect(self.ordered_selection, path)
        for idx, path in enumerate(self.ordered_selection[idx:], idx):
            newpath = (path[0] - 1,)
            del self.selection[path]
            self.selection[newpath] = True
            self.ordered_selection[idx] = newpath

        self.emit('selection-changed', self.selection)
