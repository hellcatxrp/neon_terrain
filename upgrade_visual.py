# Replace the grey test disc with the music visual.
# Does not rebuild the player. Play stays as it is.
#
# Textport:
#   exec(open(r'C:\Users\James\Desktop\TOUCH\upgrade_visual.py', encoding='utf-8').read())

_previous_name = __name__
__name__ = 'music_rack_lib'
try:
    exec(open(r'C:\Users\James\Desktop\TOUCH\build_music_rack.py', encoding='utf-8').read())
    install_visual(op('/project1/music_rack'))
finally:
    __name__ = _previous_name
