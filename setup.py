from setuptools import setup


try:
    long_description = open('README.rst').read()
except:
    long_description = 'Automatically select a display configuration based on connected devices'

setup(
    name='autorandr',

    version='1.7-1',

    description='Automatically select a display configuration based on connected devices',
    long_description=long_description,

    url='https://github.com/phillipberndt/autorandr',

    author='Phillip Berndt',
    author_email='phillip.berndt@googlemail.com',

    license='GPLv3',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Environment :: Console',

        'Intended Audience :: End Users/Desktop',

        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    keywords='xrandr',

    py_modules=['autorandr'],

    entry_points={
        'console_scripts': [
            'autorandr = autorandr:exception_handled_main',
        ],
    },
)
