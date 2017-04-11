PyWords
=======

PyWords is a simple app that helps learn new words of the foreign language. You select an unknown word and call pywords 
(it's really convenient to set a global shortcut for it). PyWords looking translation at google translate and if it succeeded shows translation. Also, PyWords will periodically ask you if you remember words that you translated with it.

Currently, only Russian and English are supported.

It's early version, so no installation process supported and a lot of hardcode in code. You can change few parameters (config dir and language) in the beginning of the pywords.py.

Installation
============

Copy all .png file into a config dir. Config dir is ~/.pywords by default. 
Schedule "pywords.py --server" to start automatically, add a shortcut on "pywords".

Troubleshooting
===============

If you icons in system tray doesn't show up, please run following commands:

gconftool-2 --type boolean --set /desktop/gnome/interface/buttons_have_icons true

gconftool-2 --type boolean --set /desktop/gnome/interface/menus_have_icons true

Dependecies
===============

python3-xlib
python3-pyqt5
python3-httplib2
