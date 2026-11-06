# Point the open music rack at VB-Cable and open the picture in its own window.
# Does not rebuild the visual. Does not change the Suno bot.
#
# Textport (Alt+T):
#   exec(open(r'C:\Users\James\Desktop\TOUCH\listen_cable.py', encoding='utf-8').read())

_previous_name = __name__
__name__ = 'music_rack_lib'
try:
    exec(open(r'C:\Users\James\Desktop\TOUCH\build_music_rack.py', encoding='utf-8').read())
    rack = op('/project1/music_rack')
    info = install_cable(rack, source='cable')
    opened = open_voice_window(rack)
finally:
    __name__ = _previous_name

_LOG = r'C:\Users\James\AppData\Local\Temp\cable_listen_log.txt'


def _write_log(lines):
    try:
        with open(_LOG, 'w', encoding='utf-8') as handle:
            handle.write('\n'.join(lines) + '\n')
    except OSError as err:
        print('music_rack: could not write log:', err)


_lines = [
    'source=%s' % info.get('source'),
    'device=%s' % info.get('device'),
    'cable=%s' % info.get('cable'),
    'hear=%s' % info.get('hear'),
    'window=%s' % opened,
    'ok=%s' % info.get('ok'),
]
_write_log(_lines)

run(
    r'''
lines = []
rack = op('/project1/music_rack')
cable = None if rack is None else rack.op('cable_in')
mono = None if rack is None else rack.op('mono')
hear = None if rack is None else rack.op('hear')

def peak(node):
    if node is None or node.numChans < 1 or node.numSamples < 1:
        return 0.0, 0, 0
    loud = 0.0
    last = node.numSamples - 1
    step = max(1, int(node.numSamples / 32))
    for c in range(node.numChans):
        chan = node[c]
        i = 0
        while i <= last:
            loud = max(loud, abs(float(chan[i])))
            i += step
        loud = max(loud, abs(float(chan[last])))
    return loud, node.numChans, node.numSamples

for label, node in (('cable', cable), ('hear', hear), ('mono', mono)):
    loud, chans, samples = peak(node)
    errs = ''
    if node is not None:
        try:
            errs = '; '.join(node.errors())
        except Exception:
            errs = ''
    lines.append('%s peak=%.5f chans=%s samples=%s errors=%s' % (label, loud, chans, samples, errs))
path = r'C:\Users\James\AppData\Local\Temp\cable_listen_log.txt'
try:
    previous = open(path, encoding='utf-8').read().rstrip('\n')
except OSError:
    previous = ''
text = (previous + '\n' if previous else '') + '\n'.join(lines) + '\n'
open(path, 'w', encoding='utf-8').write(text)
print('music_rack cable check written')
''',
    delayFrames=45,
)
