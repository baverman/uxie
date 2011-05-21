from setuptools import setup, find_packages

setup(
    name     = 'uxie',
    version  = '0.1',
    author   = 'Anton Bobrov',
    author_email = 'bobrov@vl.ru',
    description = 'GTK UX common functions and classes',
    #long_description = open('README.rst').read(),
    zip_safe   = False,
    packages = find_packages(exclude=('tests', )),
    include_package_data = True,
    url = 'http://github.com/baverman/uxie',
    classifiers = [
        "Programming Language :: Python",
        "License :: OSI Approved :: MIT License",
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications :: GTK",
        "Intended Audience :: Developers",
        "Natural Language :: English",
    ],
)
