import sys
from uxie.utils import lazy_func
from inspect import cleandoc

def test_lazy_func(tmpdir):
    package = tmpdir.mkdir('package')
    package.join('__init__.py').write('')

    package.join('func.py').write(cleandoc('''
        def func():
            return 10
    '''))

    package.join('test.py').write(cleandoc('''
        from uxie.utils import lazy_func
        import sys

        def test():
            func = lazy_func('.func.func')
            old_code = func.__code__

            result = func()
            assert result == 10

            del sys.modules['package.test']
            del sys.modules['package']

            result = func()
            assert result == 10
    '''))

    old_path = sys.path
    sys.path = [str(tmpdir)] + old_path
    __import__('package.test')
    sys.path = old_path

    sys.modules['package.test'].test()