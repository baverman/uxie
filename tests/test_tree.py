from uxie.tree import SelectionListStore

def test_selection_list_store():
    store = SelectionListStore(str)

    store.append(('one',))
    store.append(('two',))
    store.append(('three',))

    store.select((0,))
    store.select((2,))
    assert store.is_selected((0,))
    assert not store.is_selected((1,))
    assert store.is_selected((2,))

    del store[(1,)]

    assert store.is_selected((0,))
    assert store.is_selected((1,))

def test_selection_list_store_delete_from_start():
    store = SelectionListStore(str)

    store.append(('one',))
    store.append(('two',))
    store.append(('three',))

    store.select((0,))
    store.select((2,))
    del store[(0,)]

    assert not store.is_selected((0,))
    assert store.is_selected((1,))

def test_selection_list_store_delete_from_end():
    store = SelectionListStore(str)

    store.append(('one',))
    store.append(('two',))
    store.append(('three',))

    store.select((0,))
    store.select((2,))
    del store[(2,)]

    assert store.is_selected((0,))
    assert not store.is_selected((1,))

def test_selection_list_store_delete_from_mid():
    store = SelectionListStore(str)

    store.append(('one',))
    store.append(('two',))
    store.append(('three',))

    store.select((1,))
    del store[(1,)]

    assert not store.is_selected((0,))
    assert not store.is_selected((1,))