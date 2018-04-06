from setuptools import setup, find_packages

setup(
    author='Marcin Kurczewski',
    author_email='rr-@sakuya.pl',
    name='bubblesub',
    long_description='ASS subtitle editor',
    version='0.0',
    url='https://github.com/rr-/bubblesub',
    packages=find_packages(),

    entry_points={
        'console_scripts': [
            'bubblesub = bubblesub.__main__:main'
        ]
    },

    install_requires=[
        'ffms',
        'numpy',
        'scipy',
        'pyfftw',
        'PyQT5',
        'quamash',
        'regex',
        'pyenchant',
        'pympv',
        'xdg',
        'ass_tag_parser',
    ],

    classifiers=[
        'Environment :: X11 Applications :: Qt',
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Text Editors',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Multimedia :: Video',
    ])
