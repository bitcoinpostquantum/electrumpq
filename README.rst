ElectrumPQ - Lightweight BitcoinPQ client
=========================================

::

  Licence: MIT Licence
  Author: Thomas Voegtlin
  Language: Python
  Homepage: https://electrum.org/

Getting started
===============

ElectrumPQ is a pure python application. If you want to use the
Qt interface, install the Qt dependencies::

    sudo apt-get install python3-pyqt5

If you downloaded the official package (tar.gz), you can run
ElectrumPQ from its root directory, without installing it on your
system; all the python dependencies are included in the 'packages'
directory. To run ElectrumPQ from its root directory, just do::

    ./electrumpq

You can also install ElectrumPQ on your system, by running this command::

    sudo apt-get install python3-setuptools
    pip3 install .

This will download and install the Python dependencies used by
ElectrumPQ, instead of using the 'packages' directory.
The 'full' extra contains some optional dependencies that we think
are often useful but they are not strictly needed.

If you cloned the git repository, you need to compile extra files
before you can run ElectrumPQ. Read the next section, "Development
Version".

Creating Binaries
=================


To create binaries, create the 'packages' directory::

    ./contrib/make_packages

This directory contains the python dependencies used by ElectrumPQ.

Mac OS X / macOS
----------------

See `contrib/build-osx/`.

Windows
-------

See `contrib/build-wine/`.

