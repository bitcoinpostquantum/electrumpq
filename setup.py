#!/usr/bin/env python3

# python setup.py sdist --format=zip,gztar

from setuptools import setup
import os
import sys
import platform
import imp
import argparse

with open('contrib/requirements/requirements.txt') as f:
    requirements = f.read().splitlines()

with open('contrib/requirements/requirements-hw.txt') as f:
    requirements_hw = f.read().splitlines()

version = imp.load_source('version', 'lib/version.py')

if sys.version_info[:3] < (3, 4, 0):
    sys.exit("Error: ElectrumPQ requires Python version >= 3.4.0...")

data_files = []

if platform.system() in ['Linux', 'FreeBSD', 'DragonFly']:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root=', dest='root_path', metavar='dir', default='/')
    opts, _ = parser.parse_known_args(sys.argv[1:])
    usr_share = os.path.join(sys.prefix, "share")
    icons_dirname = 'pixmaps'
    if not os.access(opts.root_path + usr_share, os.W_OK) and \
       not os.access(opts.root_path, os.W_OK):
        icons_dirname = 'icons'
        if 'XDG_DATA_HOME' in os.environ.keys():
            usr_share = os.environ['XDG_DATA_HOME']
        else:
            usr_share = os.path.expanduser('~/.local/share')
    data_files += [
        (os.path.join(usr_share, 'applications/'), ['electrumpq.desktop']),
        (os.path.join(usr_share, icons_dirname), ['icons/electrumpq.png'])
    ]

setup(
    name="ElectrumPQ",
    version=version.ELECTRUM_VERSION,
    install_requires=requirements,
    extras_require={
        'full': requirements_hw + ['pycryptodomex'],
    },
    packages=[
        'electrumpq',
        'electrumpq_gui',
        'electrumpq_gui.qt',
        'electrumpq_plugins',
        'electrumpq_plugins.audio_modem',
        'electrumpq_plugins.cosigner_pool',
        'electrumpq_plugins.email_requests',
        'electrumpq_plugins.greenaddress_instant',
        'electrumpq_plugins.hw_wallet',
        'electrumpq_plugins.keepkey',
        'electrumpq_plugins.labels',
        'electrumpq_plugins.ledger',
        'electrumpq_plugins.trezor',
        'electrumpq_plugins.digitalbitbox',
        'electrumpq_plugins.trustedcoin',
        'electrumpq_plugins.virtualkeyboard',
    ],
    package_dir={
        'electrumpq': 'lib',
        'electrumpq_gui': 'gui',
        'electrumpq_plugins': 'plugins',
    },
    package_data={
        'electrumpq': [
            'servers.json',
            'servers_testnet.json',
            'servers_regtest.json',
            'currencies.json',
            'checkpoints.json',
            'checkpoints_testnet.json',
            'www/index.html',
            'wordlist/*.txt',
            'locale/*/LC_MESSAGES/electrumpq.mo',
        ]
    },
    scripts=['electrumpq'],
    data_files=data_files,
    description="Lightweight Bitcoin-PQ Wallet",
    author="Thomas Voegtlin",
    author_email="thomasv@electrum.org",
    license="MIT Licence",
    url="https://github.com/bitcoinpostquantum/electrum-bpq",
    long_description="""Lightweight Bitcoin Wallet"""
)
