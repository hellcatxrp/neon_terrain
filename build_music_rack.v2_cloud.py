# -*- coding: utf-8 -*-
# Build a music-reactive rack in the open TouchDesigner project.
#
# Textport (Alt+T), then paste this one line:
#
#   exec(open(r'C:\Users\James\Desktop\TOUCH\build_music_rack.py', encoding='utf-8').read())
#
# Play stays off. Re-running this replaces /project1/music_rack.

from __future__ import print_function

import os
import traceback

MUSIC_DIR = r'C:\Users\James\Desktop\MUSIC_SUNO'
RACK_NAME = 'music_rack'
AUDIO_EXT = ('.wav', '.flac')

CALLBACKS = r'''
import os

AUDIO_EXT = ('.wav', '.flac')
_busy = {'on': False}


def _forward(path):
    return path.replace('\\', '/')


def track_rows(folder):
    rows = []
    if not folder or not os.path.isdir(folder):
        return rows
    try:
        names = os.listdir(folder)
    except OSError as err:
        print('music_rack: cannot read folder:', err)
        return rows
    for name in names:
        full = os.path.join(folder, name)
        if not os.path.isfile(full):
            continue
        if os.path.splitext(name)[1].lower() not in AUDIO_EXT:
            continue
        rows.append((_forward(full), name))
    rows.sort(key=lambda pair: pair[1].casefold())
    return rows


def track_path(rack):
    """Menu values are row numbers. The path lives in track_menu column 0."""
    table = rack.op('track_menu')
    raw = str(rack.par.Track.eval() or '')
    if table is None or table.numRows < 1:
        return ''
    if raw.isdigit():
        row = int(raw)
        if 0 <= row < table.numRows:
            return str(table[row, 0].val)
        return ''
    for row in range(table.numRows):
        path = str(table[row, 0].val)
        label = str(table[row, 1].val) if table.numCols > 1 else ''
        if raw == path or raw == label:
            return path
    return ''


def bind_menu(rack, rows):
    table = rack.op('track_menu')
    table.clear()
    for path, label in rows:
        table.appendRow([path, label])
    table.cook(force=True)
    par = rack.par.Track
    # Do not set menuSource. TouchDesigner evaluates that field as Python,
    # so a path string is a syntax error and the menu falls back to "name1".
    if rows:
        par.menuNames = [str(i) for i in range(len(rows))]
        par.menuLabels = [label for _path, label in rows]
    else:
        par.menuNames = ['0']
        par.menuLabels = ['(no audio files)']


def apply_track(rack):
    player = rack.op('file_in')
    if player is None:
        return
    path = track_path(rack)
    if not path:
        print('music_rack: Track menu has no file path yet.')
        return
    player.par.file = path
    if hasattr(player.par, 'cuepoint'):
        player.par.cuepoint = 0
    if hasattr(player.par, 'reloadpulse'):
        player.par.reloadpulse.pulse()
    if hasattr(player.par, 'cuepulse'):
        player.par.cuepulse.pulse()
    print('music_rack track:', path)


def reload_tracks(rack):
    previous = track_path(rack)
    folder = str(rack.par.Musicfolder.eval() or '')
    rows = track_rows(folder)
    bind_menu(rack, rows)
    flac_count = sum(1 for _path, label in rows if label.lower().endswith('.flac'))
    print('music_rack: %d audio files in %s' % (len(rows), folder))
    if flac_count:
        print('music_rack: %d of those are flac. This build documents wav, mp3, and aif. If a flac shows an error, pick a wav.' % flac_count)
    if not rows:
        print('music_rack: no wav or flac files found.')
        return
    paths = [path for path, _label in rows]
    if previous in paths:
        pick = str(paths.index(previous))
    else:
        wav_rows = [i for i, path in enumerate(paths) if path.lower().endswith('.wav')]
        pick = str(wav_rows[0] if wav_rows else 0)
    _busy['on'] = True
    try:
        rack.par.Track = pick
    finally:
        _busy['on'] = False
    apply_track(rack)


def onValueChange(par, prev):
    if _busy['on']:
        return
    rack = par.owner
    if par.name == 'Track':
        apply_track(rack)
    elif par.name == 'Musicfolder':
        reload_tracks(rack)
    return


def onValuesChanged(changes):
    for change in changes:
        onValueChange(change.par, getattr(change, 'prev', None))
    return


def onPulse(par):
    if par.name == 'Reloadtracks':
        reload_tracks(par.owner)
    return


def onExpressionChange(par, prev):
    return


def onExportChange(par, prev):
    return
'''


def as_par(result):
    if isinstance(result, (list, tuple)):
        return result[0]
    return result


def td_type(*names):
    """Look up a TouchDesigner operator type. Names differ from the menu label."""
    import builtins
    scopes = []
    if isinstance(__builtins__, dict):
        scopes.append(__builtins__)
    else:
        scopes.append(vars(builtins))
    scopes.append(globals())
    for name in names:
        for scope in scopes:
            if name in scope:
                return scope[name]
    hits = []
    seen = set()
    for scope in scopes:
        for key in list(scope):
            if not isinstance(key, str) or key in seen:
                continue
            seen.add(key)
            low = key.lower()
            if 'execute' in low and 'param' in low and low.endswith('dat'):
                hits.append(key)
    if len(hits) == 1:
        print('music_rack: using operator type %s' % hits[0])
        for scope in scopes:
            if hits[0] in scope:
                return scope[hits[0]]
    raise NameError('Parameter Execute type not found. Tried %s. Nearby: %s' % (list(names), hits))


def choose(par, *options):
    available = list(par.menuNames) if hasattr(par, 'menuNames') else []
    for opt in options:
        if opt in available:
            par.val = opt
            return opt
    print('music_rack: could not set %s %s. Options: %s' % (par.owner.path, par.name, available))
    return None


def set_expr(owner, name, expr):
    if not hasattr(owner.par, name):
        print('music_rack: missing parameter %s on %s' % (name, owner.path))
        return False
    getattr(owner.par, name).expr = expr
    return True


def set_first_expr(owner, options):
    for name, expr in options:
        if hasattr(owner.par, name):
            getattr(owner.par, name).expr = expr
            return name
    print('music_rack: none of %s exist on %s' % ([name for name, _expr in options], owner.path))
    return None


def wire(dst, src, index=0):
    connectors = list(dst.inputConnectors)
    if index < 0 or index >= len(connectors):
        print('music_rack: %s has %s inputs, so input %s was not connected.' % (
            dst.path, len(connectors), index))
        return False
    connectors[index].connect(src)
    return True


def feed_chop(image, source):
    """CHOP to TOP has no input connector. The source is its CHOP parameter."""
    if not hasattr(image.par, 'chop'):
        names = [p.name for p in image.pars() if 'chop' in p.name.lower()]
        print('music_rack: %s has no CHOP parameter. Nearby: %s' % (image.path, names))
        return False
    image.par.chop = source
    return True


def size_data_image(image, source):
    """One pixel per sample. A default TOP size pads the curve with zeros and flattens it."""
    try:
        source.cook(force=True)
        samples = int(source.numSamples)
        chans = int(source.numChans)
    except Exception as err:
        print('music_rack: could not measure %s: %s' % (source.path, err))
        return
    if samples < 1 or chans < 1:
        print('music_rack: %s is empty, so %s keeps its default size.' % (source.path, image.path))
        return
    set_top_res(image, samples, chans)
    if hasattr(image.par, 'resmult'):
        image.par.resmult = False
    if hasattr(image.par, 'format'):
        choose(image.par.format, 'rgba32float', 'rgba16float')


def bind_uniforms(visual, uniforms):
    """The GLSL TOP has no built-in clock. Each uniform is one vec block on the Vectors page."""
    seq = None
    try:
        seq = visual.seq.vec
    except Exception:
        seq = None
    if seq is not None:
        try:
            if int(seq.numBlocks) < len(uniforms):
                seq.numBlocks = len(uniforms)
        except Exception as err:
            print('music_rack: uniform slots:', err)
    bound = True
    for index, (name, expr) in enumerate(uniforms):
        name_par = 'vec%dname' % index
        value_par = 'vec%dvaluex' % index
        if not hasattr(visual.par, name_par) or not hasattr(visual.par, value_par):
            names = [p.name for p in visual.pars() if 'vec' in p.name.lower()]
            print('music_rack: could not bind uniform %s. Nearby: %s' % (name, names[:30]))
            bound = False
            continue
        setattr(visual.par, name_par, name)
        getattr(visual.par, value_par).expr = expr
    return bound


def prepare_spectrum(rack, spectrum):
    """Return a CHOP whose samples are the raw frequency curve. spec_shape bands and scales it."""
    spec_mag = place(rack.create(selectCHOP, 'spec_mag'), 700, -80)
    spec_mag.par.channames = '*'
    if hasattr(spec_mag.par, 'timeslice'):
        spec_mag.par.timeslice = True
    wire(spec_mag, spectrum)

    try:
        spec_mag.cook(force=True)
        names = [c.name for c in spec_mag.chans()]
        chosen = None
        for token in ('_m', 'mag'):
            for name in names:
                if token in name.lower():
                    chosen = name
                    break
            if chosen:
                break
        if chosen is None and names:
            chosen = names[0]
        if chosen:
            spec_mag.par.channames = chosen
            spec_mag.cook(force=True)
        print('music_rack: spectrum channel %s (%s channels, %s samples)' % (
            chosen or '*', spec_mag.numChans, spec_mag.numSamples))
    except Exception as err:
        print('music_rack: spectrum select:', err)

    source = spec_mag
    try:
        source.cook(force=True)
        if source.numChans > max(1, int(source.numSamples)):
            swapped = place(rack.create(shuffleCHOP, 'spec_order'), 840, -80)
            if hasattr(swapped.par, 'method'):
                choose(swapped.par.method, 'swap')
            if hasattr(swapped.par, 'timeslice'):
                swapped.par.timeslice = True
            wire(swapped, source)
            source = swapped
            source.cook(force=True)
            print('music_rack: spectrum was in channels, swapped into %s samples.' % source.numSamples)
    except Exception as err:
        print('music_rack: spectrum reshape:', err)
    return source


def spectrum_is_log(spectrum):
    """Some Audio Spectrum modes already space the bins logarithmically. Do not do it twice."""
    toggle = None
    mode_log = False
    hints = []
    for par in spectrum.pars():
        low = par.name.lower()
        try:
            val = par.eval()
        except Exception:
            continue
        if 'log' in low and 'freq' in low and getattr(par, 'isToggle', False):
            hints.append('%s=%s' % (par.name, val))
            toggle = bool(val) or bool(toggle)
        elif 'mode' in low and getattr(par, 'isMenu', False):
            hints.append('%s=%s' % (par.name, val))
            if 'vis' in str(val).lower():
                mode_log = True
    log = toggle if toggle is not None else mode_log
    print('music_rack: spectrum settings %s, bins treated as %s' % (
        hints, 'log-spaced' if log else 'linear'))
    return log


def place(node, x, y):
    node.nodeX = x
    node.nodeY = y
    return node


def make_filter(rack, name, kind, cutoff, x, y):
    filt = place(rack.create(audiofilterCHOP, name), x, y)
    choose(filt.par.filter, kind)
    if hasattr(filt.par, 'units'):
        choose(filt.par.units, 'frequency')
    if hasattr(filt.par, 'cutofffrequency'):
        filt.par.cutofffrequency = cutoff
    if hasattr(filt.par, 'resonance'):
        filt.par.resonance = 0
    if hasattr(filt.par, 'rolloff'):
        filt.par.rolloff = 24
    if hasattr(filt.par, 'drywet'):
        filt.par.drywet = 1
    return filt


def make_analyze(rack, name, x, y):
    node = place(rack.create(analyzeCHOP, name), x, y)
    choose(node.par.function, 'rmspower')
    if hasattr(node.par, 'timeslice'):
        node.par.timeslice = True
    return node


def make_gain(rack, name, gain_par, x, y):
    node = place(rack.create(mathCHOP, name), x, y)
    if hasattr(node.par, 'gain'):
        set_expr(node, 'gain', 'parent().par.%s' % gain_par)
    else:
        print('music_rack: %s has no Multiply/gain parameter' % node.path)
    return node


def make_limit(rack, name, x, y):
    node = place(rack.create(limitCHOP, name), x, y)
    if hasattr(node.par, 'type'):
        choose(node.par.type, 'clamp')
    if hasattr(node.par, 'min'):
        node.par.min = 0
    if hasattr(node.par, 'max'):
        node.par.max = 1
    return node


def make_lag(rack, name, up, down, channel, x, y):
    node = place(rack.create(lagCHOP, name), x, y)
    if hasattr(node.par, 'lagmethod'):
        choose(node.par.lagmethod, 'amp', 'value')
    if hasattr(node.par, 'lag1'):
        node.par.lag1 = up
    if hasattr(node.par, 'lag2'):
        node.par.lag2 = down
    if hasattr(node.par, 'lagunit'):
        choose(node.par.lagunit, 'seconds')
    if hasattr(node.par, 'timeslice'):
        node.par.timeslice = True
    if hasattr(node.par, 'commonrenamefrom'):
        node.par.commonrenamefrom = '*'
        node.par.commonrenameto = channel
    return node


def set_top_res(node, width, height):
    if hasattr(node.par, 'outputresolution'):
        choose(node.par.outputresolution, 'custom')
    if hasattr(node.par, 'resolutionw'):
        node.par.resolutionw = width
    if hasattr(node.par, 'resolutionh'):
        node.par.resolutionh = height


def add_float(page, name, label, default, lo, hi):
    par = as_par(page.appendFloat(name, label=label))
    par.default = default
    par.normMin = lo
    par.normMax = hi
    par.min = lo
    par.max = hi
    par.clampMin = True
    par.clampMax = True
    par.val = default
    return par


VISUAL_CONTROLS = (
    ('Motion', 'Motion', 1.0, 0, 3),
    ('Punch', 'Kick Punch', 1.0, 0, 2),
    ('Onsetthresh', 'Onset Threshold', 0.35, 0.05, 1),
)


def add_controls(rack):
    page = rack.appendCustomPage('Music')

    track = as_par(page.appendMenu('Track', label='Track'))

    play = as_par(page.appendToggle('Play', label='Play'))
    play.default = False
    play.val = False

    add_float(page, 'Volume', 'Volume', 0.25, 0, 1)
    add_float(page, 'Lowgain', 'Low Gain', 4, 0, 20)
    add_float(page, 'Midgain', 'Mid Gain', 5, 0, 20)
    add_float(page, 'Highgain', 'High Gain', 6, 0, 20)
    add_float(page, 'Rmsgain', 'RMS Gain', 3, 0, 20)
    add_float(page, 'Kickthresh', 'Kick Threshold', 0.3, 0, 1)
    for spec in VISUAL_CONTROLS:
        add_float(page, *spec)

    as_par(page.appendPulse('Reloadtracks', label='Reload Tracks'))

    folder = as_par(page.appendStr('Musicfolder', label='Music Folder'))
    folder.default = MUSIC_DIR
    folder.val = MUSIC_DIR
    return track


def ensure_visual_controls(rack):
    """Racks built before the visual rework lack the visual sliders. Add them in place."""
    page = None
    for existing in rack.customPages:
        if existing.name == 'Music':
            page = existing
            break
    if page is None:
        page = rack.appendCustomPage('Music')
    for spec in VISUAL_CONTROLS:
        if not hasattr(rack.par, spec[0]):
            add_float(page, *spec)


def add_folder_dat(rack):
    folder = place(rack.create(folderDAT, 'music_folder'), -900, 480)
    folder.par.rootfolder = MUSIC_DIR
    if hasattr(folder.par, 'refresh'):
        folder.par.refresh = True
    if hasattr(folder.par, 'subfolders'):
        folder.par.subfolders = False
    if hasattr(folder.par, 'allextensions'):
        folder.par.allextensions = False
    if hasattr(folder.par, 'imageextensions'):
        folder.par.imageextensions = False
    if hasattr(folder.par, 'movieextensions'):
        folder.par.movieextensions = False
    if hasattr(folder.par, 'audioextensions'):
        folder.par.audioextensions = True
    if hasattr(folder.par, 'extensions'):
        folder.par.extensions = 'wav flac'
    folder.cook(force=True)
    return folder


def add_callbacks(rack):
    table = place(rack.create(tableDAT, 'track_menu'), -560, 480)
    callbacks = place(
        rack.create(td_type('parameterexecuteDAT', 'parexecDAT', 'parexecuteDAT'), 'music_callbacks'),
        -220, 480)
    callbacks.text = CALLBACKS
    callbacks.par.active = False
    try:
        callbacks.par.op = rack
    except Exception:
        callbacks.par.op = rack.path
    if hasattr(callbacks.par, 'pars'):
        callbacks.par.pars = '*'
    if hasattr(callbacks.par, 'custom'):
        callbacks.par.custom = True
    if hasattr(callbacks.par, 'builtin'):
        callbacks.par.builtin = False
    for name in ('valuechange', 'onpulse'):
        if hasattr(callbacks.par, name):
            setattr(callbacks.par, name, True)
    if hasattr(callbacks.par, 'valueschanged'):
        callbacks.par.valueschanged = False
    return table, callbacks


def add_readme(rack):
    note = place(rack.create(textDAT, 'readme'), 120, 480)
    note.text = '\n'.join([
        'music_rack',
        '',
        'Select this component. The Music page is on the right.',
        'Pick a Track, set Volume, then turn Play on.',
        '',
        'audio_out channels, all roughly 0 to 1:',
        '  low   bass, fast attack, slower release',
        '  mid   180 Hz to 2200 Hz',
        '  high  above 4000 Hz',
        '  rms   overall loudness',
        '  kick  short envelope when low crosses Kick Threshold',
        '',
        'spectrum is the raw frequency curve.',
        '',
        'preview is the picture. It reads its own features, not audio_out:',
        '  vis_features  raw band levels, auto-gained per track, kick onsets,',
        '                section energy, and a music clock that runs faster when loud',
        '  spec_shape    64 log-spaced spectrum bands, bass first, in a steady dB range',
        'Motion scales how fast the picture moves with the music.',
        'Kick Punch scales the zoom, ring, and flash on each kick.',
        'Onset Threshold: lower catches more kicks, higher only the hard ones.',
        'Low/Mid/High/RMS Gain and Kick Threshold only shape audio_out.',
        '',
        'New files: drop them in the music folder, then pulse Reload Tracks.',
        'Visuals you build later should read only audio_out (and spectrum if they need the curve).',
        'Running the build script again replaces this whole component.',
    ])
    return note


FEATURE_SOURCES = ('an_low', 'an_mid', 'an_high', 'an_rms')

# Script CHOP: visual-only features, one sample per channel.
# Reads the raw RMS levels, so the Gain sliders and the 0..1 clamp in audio_out
# do not flatten it. Every band is divided by its own slow peak, so quiet and
# loud masters both use the full range, while a breakdown still reads quieter
# than the drop before it.
FEATURE_CALLBACKS = r'''
import math

SOURCES = ('an_low', 'an_mid', 'an_high', 'an_rms')
BANDS = ('low', 'mid', 'high', 'rms')
NAMES = ('low', 'mid', 'high', 'rms', 'kick', 'section', 'flux', 'time')
FLOOR = 0.002       # below this a band counts as silence, not something to amplify
PEAK_TAU = 12.0     # seconds for the auto-gain peak to fall back
SMOOTH = {          # attack, release in seconds
    'low': (0.015, 0.18),
    'mid': (0.02, 0.15),
    'high': (0.01, 0.10),
    'rms': (0.03, 0.25),
}

_s = {
    'frame': None,
    'peak': dict.fromkeys(BANDS, FLOOR),
    'out': dict.fromkeys(BANDS, 0.0),
    'slow_low': 0.0,
    'flux': 0.0,
    'flux_peak': 0.05,
    'flux_prev': 0.0,
    'since_kick': 1.0,
    'kick': 0.0,
    'section': 0.0,
    'time': 0.0,
}


def _last(node):
    if node is None or node.numChans < 1 or node.numSamples < 1:
        return 0.0
    return max(0.0, float(node[0][node.numSamples - 1]))


def _par(scriptOp, name, default):
    par = getattr(scriptOp.parent().par, name, None)
    return float(par.eval()) if par is not None else default


def _follow(cur, target, up, down, dt):
    tau = up if target > cur else down
    if tau <= 0:
        return target
    return cur + (target - cur) * (1.0 - math.exp(-dt / tau))


def _update(scriptOp, dt):
    rack = scriptOp.parent()
    decay = math.exp(-dt / PEAK_TAU)
    norm = {}
    for source, name in zip(SOURCES, BANDS):
        raw = _last(rack.op(source))
        peak = max(raw, _s['peak'][name] * decay, FLOOR)
        _s['peak'][name] = peak
        norm[name] = min(1.0, max(0.0, (raw / peak - 0.1) / 0.9))
        up, down = SMOOTH[name]
        _s['out'][name] = _follow(_s['out'][name], norm[name], up, down, dt)

    # Onset: how far the bass jumps above its own recent average.
    # A level threshold misses kicks on bass-heavy tracks; a jump does not.
    low = norm['low']
    _s['slow_low'] = _follow(_s['slow_low'], low, 0.25, 0.25, dt)
    flux = max(0.0, low - _s['slow_low'])
    _s['flux_peak'] = max(flux, _s['flux_peak'] * math.exp(-dt / 8.0), 0.05)
    flux_n = flux / _s['flux_peak']
    thresh = _par(scriptOp, 'Onsetthresh', 0.35)
    _s['since_kick'] += dt
    if (flux_n >= thresh and _s['flux_prev'] < thresh
            and _s['since_kick'] > 0.11 and low > 0.15):
        _s['kick'] = max(_s['kick'], min(1.0, 0.55 + flux_n * 0.45))
        _s['since_kick'] = 0.0
    else:
        _s['kick'] *= math.exp(-dt / 0.16)
    _s['flux_prev'] = flux_n
    _s['flux'] = min(1.0, flux_n)

    energy = _s['out']['rms'] * 0.7 + _s['out']['low'] * 0.3
    _s['section'] = _follow(_s['section'], energy, 6.0, 6.0, dt)

    # Music clock: crawls in breakdowns, runs in drops, lurches on kicks.
    motion = _par(scriptOp, 'Motion', 1.0)
    _s['time'] += dt * motion * (0.12 + 0.9 * energy ** 1.5 + 0.8 * _s['kick'])


def onSetupParameters(scriptOp):
    return


def onPulse(par):
    return


def onCook(scriptOp):
    # Reading absTime.frame also makes this cook every frame, so kicks decay
    # and the clock advances even between audio updates.
    frame = absTime.frame
    last = _s['frame']
    if last is None or frame < last:
        dt = 1.0 / 60.0
    else:
        dt = (frame - last) / float(project.cookRate or 60)
    _s['frame'] = frame
    dt = min(dt, 0.1)
    if dt > 0:
        _update(scriptOp, dt)

    values = dict(_s['out'])
    values.update(kick=_s['kick'], section=_s['section'], flux=_s['flux'], time=_s['time'])
    scriptOp.clear()
    scriptOp.numSamples = 1
    for name in NAMES:
        scriptOp.appendChan(name)[0] = values[name]
    return
'''

# Script CHOP: the spectrum as 64 log-spaced bands, 0..1, bass first.
# Converted to dB, tilted +3 dB per octave so treble is not buried, and scaled
# against a slowly falling reference. Loud passages stay taller than quiet ones,
# unlike a per-frame min/max stretch.
SPEC_CALLBACKS = r'''
import math
import numpy as np

LOG_INPUT = __LOG_INPUT__   # True when the Audio Spectrum CHOP already spaces bins logarithmically
BANDS = 64
LO_HZ = 30.0
HI_HZ = 16000.0
NYQUIST = 22050.0
RANGE_DB = 48.0
GATE_DB = -100.0
REF_FALL = 4.0      # dB per second the loudness reference may drop
ATTACK = 0.02
RELEASE = 0.20

if LOG_INPUT:
    TILT = np.zeros(BANDS)
else:
    TILT = 3.0 * np.log2(np.geomspace(LO_HZ, HI_HZ, BANDS) / LO_HZ)

_s = {'frame': None, 'ref': GATE_DB, 'smooth': np.zeros(BANDS), 'edges': None, 'count': 0}


def _edges(count):
    if LOG_INPUT:
        e = np.linspace(0, count, BANDS + 1)
    else:
        e = np.geomspace(LO_HZ, HI_HZ, BANDS + 1) / NYQUIST * count
    e = np.clip(np.floor(e).astype(int), 0, count - 1)
    lo = e[:-1]
    hi = np.minimum(np.maximum(e[1:], lo + 1), count)
    return lo, hi


def _target(scriptOp, dt):
    inp = scriptOp.inputs[0] if scriptOp.inputs else None
    if inp is None or inp.numChans < 1 or inp.numSamples < 2:
        return np.zeros(BANDS)
    raw = np.asarray(inp[0].numpyArray(), dtype=np.float64)
    count = raw.shape[0]
    if count != _s['count']:
        _s['edges'] = _edges(count)
        _s['count'] = count
    if raw.min() < 0.0:
        db = raw    # already decibels
    else:
        db = 20.0 * np.log10(raw + 1e-7)
    lo, hi = _s['edges']
    bands = np.array([db[a:b].max() for a, b in zip(lo, hi)]) + TILT
    _s['ref'] = max(float(bands.max()), _s['ref'] - REF_FALL * dt, GATE_DB)
    if _s['ref'] <= GATE_DB + 1.0:
        return np.zeros(BANDS)
    return np.clip((bands - (_s['ref'] - RANGE_DB)) / RANGE_DB, 0.0, 1.0)


def onSetupParameters(scriptOp):
    return


def onPulse(par):
    return


def onCook(scriptOp):
    frame = absTime.frame
    last = _s['frame']
    if last is None or frame < last:
        dt = 1.0 / 60.0
    else:
        dt = (frame - last) / float(project.cookRate or 60)
    _s['frame'] = frame
    dt = min(dt, 0.1)
    if dt > 0:
        target = _target(scriptOp, dt)
        smooth = _s['smooth']
        coef = np.where(target > smooth,
                        1.0 - math.exp(-dt / ATTACK),
                        1.0 - math.exp(-dt / RELEASE))
        _s['smooth'] = smooth + (target - smooth) * coef

    scriptOp.clear()
    scriptOp.numSamples = BANDS
    chan = scriptOp.appendChan('spec')
    for i in range(BANDS):
        chan[i] = float(_s['smooth'][i])
    return
'''


VISUAL_SHADER = r'''
layout(location = 0) out vec4 fragColor;
uniform float uTime;    // music clock from vis_features, not wall time
uniform float uPunch;   // Kick Punch slider

// Input 0, one row from vis_features:
//   0 low, 1 mid, 2 high, 3 rms, 4 kick, 5 section, 6 flux
// Input 1, one row of 64 spectrum bands from spec_shape, bass first, 0..1.

float feature(int i)
{
    ivec2 s = textureSize(sTD2DInputs[0], 0);
    if (s.x >= s.y) {
        return i < s.x ? texelFetch(sTD2DInputs[0], ivec2(i, 0), 0).r : 0.0;
    }
    return i < s.y ? texelFetch(sTD2DInputs[0], ivec2(0, i), 0).r : 0.0;
}

float specAt(int i, ivec2 s)
{
    return s.x >= s.y
        ? texelFetch(sTD2DInputs[1], ivec2(i, 0), 0).r
        : texelFetch(sTD2DInputs[1], ivec2(0, i), 0).r;
}

// u = 0 is bass, u = 1 is treble. Interpolated so the bands do not step.
float spec(float u)
{
    ivec2 s = textureSize(sTD2DInputs[1], 0);
    int n = max(s.x, s.y);
    if (n < 2) {
        return 0.0;
    }
    float x = clamp(u, 0.0, 1.0) * float(n - 1);
    int i0 = int(floor(x));
    int i1 = min(i0 + 1, n - 1);
    return clamp(mix(specAt(i0, s), specAt(i1, s), x - float(i0)), 0.0, 1.0);
}

float hash21(vec2 p)
{
    p = fract(p * vec2(123.34, 345.45));
    p += dot(p, p + 34.345);
    return fract(p.x * p.y);
}

float noise(vec2 p)
{
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = hash21(i);
    float b = hash21(i + vec2(1.0, 0.0));
    float c = hash21(i + vec2(0.0, 1.0));
    float d = hash21(i + vec2(1.0, 1.0));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float fbm(vec2 p)
{
    float v = 0.0;
    float a = 0.5;
    for (int i = 0; i < 4; i++) {
        v += a * noise(p);
        p = p * 2.03 + vec2(1.7, 9.2);
        a *= 0.5;
    }
    return v;
}

vec3 palette(float t)
{
    float x = fract(t) * 4.0;
    vec3 c0 = vec3(0.96, 0.16, 0.62);
    vec3 c1 = vec3(0.18, 0.42, 1.00);
    vec3 c2 = vec3(0.05, 0.95, 0.82);
    vec3 c3 = vec3(1.00, 0.58, 0.10);
    if (x < 1.0) return mix(c0, c1, x);
    if (x < 2.0) return mix(c1, c2, x - 1.0);
    if (x < 3.0) return mix(c2, c3, x - 2.0);
    return mix(c3, c0, x - 3.0);
}

// Embers rise with the music clock. Columns never scroll sideways, so each
// ember sits over a fixed frequency: bass in the middle, treble at the edges.
vec3 sparkLayer(vec2 uv, float t, vec2 grid, float rise, float size, float hue, float seed)
{
    vec2 p = uv * grid;
    p.y -= t * rise;
    vec2 id = floor(p);
    vec2 gv = fract(p) - 0.5;
    float n = hash21(id + seed);
    float n2 = hash21(id + seed + 19.1);
    vec2 wobble = 0.08 * vec2(
        sin(t * (0.8 + n) + n * 6.28318),
        cos(t * (0.55 + n2) + n2 * 6.28318));
    vec2 c = (vec2(n, n2) - 0.5) * 0.7 + wobble;
    vec2 d = gv - c;
    float sx = (id.x + 0.5 + c.x) / grid.x;
    float band = spec(abs(sx - 0.5) * 2.0);
    float rad = mix(0.05, 0.2, n2) * size * (0.6 + band * 0.8);
    float glow = exp(-dot(d, d) / max(rad * rad, 0.0001));
    float core = exp(-dot(d, d) / max(rad * rad * 0.1, 0.00005));
    float keep = step(0.35, n);
    float twinkle = 0.7 + 0.3 * sin(t * 3.0 + n * 20.0);
    float amp = keep * twinkle * (0.03 + pow(band, 1.6) * 1.3);
    vec3 tint = palette(hue + n * 0.5 + band * 0.2);
    return tint * glow * amp + vec3(1.0, 0.96, 0.92) * core * amp * 0.5;
}

void main()
{
    float t = uTime;
    vec2 uv = vUV.st;
    float low = clamp(feature(0), 0.0, 1.0);
    float mid = clamp(feature(1), 0.0, 1.0);
    float high = clamp(feature(2), 0.0, 1.0);
    float rms = clamp(feature(3), 0.0, 1.0);
    float kick = clamp(feature(4), 0.0, 1.0);
    float section = clamp(feature(5), 0.0, 1.0);
    float punch = kick * uPunch;
    float energy = clamp(rms * 0.7 + low * 0.3, 0.0, 1.0);

    // Section energy picks the palette, so colour changes with verse and drop.
    float hue = section * 0.45 + t * 0.012;

    // Bass breathes the frame; kicks punch it in.
    vec2 p = (uv - 0.5) * vec2(1.7778, 1.0);
    float rad = length(p);
    vec2 w = p * 1.45 * (1.0 - low * 0.10 - punch * 0.16);
    w += vec2(sin(w.y * 2.2 + t * 0.65) * 0.08, sin(w.x * 1.6 - t * 0.4) * 0.06);

    // Mids stir the cloud harder.
    float warp = 2.2 + mid * 2.6;
    vec2 q = vec2(
        fbm(w + vec2(0.0, t * 0.08)),
        fbm(w + vec2(5.2, 1.3) - t * 0.055));
    vec2 r = vec2(
        fbm(w + warp * q + vec2(1.7, 9.2) + t * 0.07),
        fbm(w + warp * q + vec2(8.3, 2.8) - t * 0.05));
    float f = fbm(w * 1.1 + warp * r);

    vec3 cA = palette(hue + f * 0.6 + q.x * 0.35);
    vec3 cB = palette(hue + 0.35 + r.y * 0.45 + high * 0.15);
    float body = smoothstep(0.2, 0.95, f);
    float ridge = pow(smoothstep(0.4, 0.95, f), 1.6);

    // Dark at rest. Loudness supplies the light.
    vec3 col = vec3(0.012, 0.006, 0.03);
    col += cA * body * (0.08 + energy * 0.75);
    col += cB * ridge * (0.06 + low * 1.1 + punch * 0.6);
    col += cA.bgr * pow(clamp(length(q), 0.0, 1.0), 1.5) * high * 0.45;

    float core = exp(-rad * rad * (3.0 - low * 1.6));
    col += palette(hue + 0.55) * core * (0.04 + low * 0.9);

    // Kick: a ring that runs outward as the envelope decays, plus a short flash.
    float ringR = 0.05 + (1.0 - kick) * 1.1;
    float ringW = 0.025 + 0.06 * (1.0 - kick);
    float rd = (rad - ringR) / ringW;
    float ring = exp(-rd * rd);
    col += palette(hue + 0.1 + high * 0.1) * ring * punch * 1.2;
    col += vec3(1.0, 0.95, 0.9) * punch * 0.18 * exp(-rad * rad * 1.2);

    // Spectrum curtain along the bottom, mirrored: bass in the middle.
    float u = abs(uv.x - 0.5) * 2.0;
    float sv = spec(u);
    float top = 0.03 + sv * 0.45;
    float curtain = sv * sv * exp(-uv.y / (0.04 + sv * 0.3));
    float ed = (uv.y - top) / 0.006;
    float edge = sv * exp(-ed * ed);
    col += palette(hue + 0.2 + u * 0.5) * (curtain * 0.7 + edge * 0.5);

    col += sparkLayer(uv, t, vec2(8.0, 4.5), 0.25, 1.5, hue, 0.0);
    col += sparkLayer(uv, t, vec2(16.0, 9.0), 0.40, 1.05, hue, 7.3);
    col += sparkLayer(uv, t, vec2(32.0, 18.0), 0.70, 0.72, hue, 13.9) * (0.5 + high);

    float luma = dot(col, vec3(0.299, 0.587, 0.114));
    col = mix(vec3(luma), col, 1.15 + high * 0.25);
    col = 1.0 - exp(-max(col, 0.0) * 1.25);
    fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));
}
'''


def destroy_named(rack, name):
    node = rack.op(name)
    if node is None:
        return
    try:
        docked = list(node.docked)
    except Exception:
        docked = []
    for extra in docked:
        try:
            extra.destroy()
        except Exception:
            pass
    node.destroy()


def make_script_chop(rack, name, text, x, y):
    """Script CHOP with its callbacks replaced by text."""
    node = place(rack.create(scriptCHOP, name), x, y)
    dat = None
    if hasattr(node.par, 'callbacks'):
        try:
            dat = node.par.callbacks.eval()
        except Exception:
            dat = None
    if dat is None:
        dat = place(rack.create(textDAT, name + '_callbacks'), x, y - 140)
        node.par.callbacks = dat
    dat.text = text
    return node


def install_visual(rack):
    """Replace the picture with the music-driven cloud.

    Leaves the player, the track menu, and audio_out alone. The picture reads
    the raw band levels through vis_features and the spectrum through spec_shape.
    """
    if rack is None:
        print('music_rack: /project1/music_rack is missing.')
        return None

    for name in (
        'preview', 'picture', 'level', 'brightness', 'color', 'motion', 'circle', 'bg',
        'visual', 'visual_shader', 'levels_samples', 'levels_image',
        'spec_mag', 'spec_order', 'spec_bins', 'spec_lag', 'spec_gain', 'spec_limit', 'spec_image',
        'vis_features', 'vis_features_callbacks', 'spec_shape', 'spec_shape_callbacks',
    ):
        destroy_named(rack, name)

    spectrum = rack.op('spectrum')
    missing = [name for name in FEATURE_SOURCES + ('spectrum',) if rack.op(name) is None]
    if missing:
        print('music_rack: %s missing. Run the full build first.' % missing)
        return None

    ensure_visual_controls(rack)

    features = make_script_chop(rack, 'vis_features', FEATURE_CALLBACKS, 420, 80)

    levels = place(rack.create(shuffleCHOP, 'levels_samples'), 700, 80)
    if hasattr(levels.par, 'method'):
        choose(levels.par.method, 'swap')
    if hasattr(levels.par, 'timeslice'):
        levels.par.timeslice = True
    wire(levels, features)

    levels_image = place(rack.create(choptoTOP, 'levels_image'), 980, 80)
    if hasattr(levels_image.par, 'dataformat'):
        choose(levels_image.par.dataformat, 'r', 'red')
    if hasattr(levels_image.par, 'layout'):
        choose(levels_image.par.layout, 'rowscropped')
    if hasattr(levels_image.par, 'clamp'):
        levels_image.par.clamp = False
    feed_chop(levels_image, levels)
    size_data_image(levels_image, levels)

    bins = prepare_spectrum(rack, spectrum)
    log_input = spectrum_is_log(spectrum)
    shaper = make_script_chop(
        rack, 'spec_shape',
        SPEC_CALLBACKS.replace('__LOG_INPUT__', 'True' if log_input else 'False'),
        1260, -80)
    wire(shaper, bins)

    spec_image = place(rack.create(choptoTOP, 'spec_image'), 1820, -80)
    if hasattr(spec_image.par, 'dataformat'):
        choose(spec_image.par.dataformat, 'r', 'red')
    if hasattr(spec_image.par, 'layout'):
        choose(spec_image.par.layout, 'rowscropped')
    if hasattr(spec_image.par, 'clamp'):
        spec_image.par.clamp = False
    feed_chop(spec_image, shaper)
    size_data_image(spec_image, shaper)

    shader = place(rack.create(textDAT, 'visual_shader'), 980, -280)
    shader.text = VISUAL_SHADER
    visual = place(rack.create(glslTOP, 'visual'), 1540, 80)
    set_top_res(visual, 1280, 720)
    if hasattr(visual.par, 'format'):
        choose(visual.par.format, 'rgba16float', 'rgba8fixed')
    if hasattr(visual.par, 'inputfiltertype'):
        choose(visual.par.inputfiltertype, 'nearest')
    if hasattr(visual.par, 'fillmode'):
        choose(visual.par.fillmode, 'best')
    if hasattr(visual.par, 'pixeldat'):
        visual.par.pixeldat = shader
    else:
        print('music_rack: GLSL TOP has no pixeldat parameter.')
        print('  shader parameters:', [p.name for p in visual.pars() if 'dat' in p.name.lower() or 'shader' in p.name.lower()])
    bind_uniforms(visual, [
        ('uTime', "op('vis_features')['time']"),
        ('uPunch', 'parent().par.Punch'),
    ])
    wire(visual, levels_image, 0)
    wire(visual, spec_image, 1)
    visual.viewer = True

    preview = place(rack.create(nullTOP, 'preview'), 1820, 80)
    wire(preview, visual)
    preview.viewer = True
    preview.display = True
    preview.color = (0.35, 0.6, 1.0)
    if hasattr(preview.par, 'fillmode'):
        choose(preview.par.fillmode, 'best')

    try:
        preview.cook(force=True)
    except Exception as err:
        print('music_rack cook:', err)
    report(features)
    report(shaper)
    report(visual)
    report(preview)
    try:
        features.cook(force=True)
        shaper.cook(force=True)
        levels_image.cook(force=True)
        spec_image.cook(force=True)
        print('music_rack: features %s' % [c.name for c in features.chans()])
        print('music_rack: spectrum source %s samples -> %s bands' % (bins.numSamples, shaper.numSamples))
        print('music_rack: level image %sx%s, spectrum image %sx%s' % (
            levels_image.width, levels_image.height, spec_image.width, spec_image.height))
    except Exception as err:
        print('music_rack: analysis check failed:', err)

    try:
        preview.selected = True
        preview.openViewer()
    except Exception as err:
        print('music_rack: viewer did not open by itself (%s). Click preview and press v.' % err)

    print('')
    print('A window should be open on preview.')
    print('Silence is nearly black. Loudness lights the cloud, bass makes it breathe,')
    print('kicks punch in with a ring, and the bottom curtain is the spectrum (bass in the middle).')
    print('Motion speeds up in loud sections and nearly stops in quiet ones.')
    print('Tune on the Music page: Motion, Kick Punch, Onset Threshold.')
    return preview


def build_preview(rack):
    return install_visual(rack)


def report(node):
    try:
        errs = node.errors()
    except Exception:
        return
    if errs:
        print('music_rack error on %s: %s' % (node.path, errs))


def build():
    root = op('/project1')
    if root is None:
        print('music_rack: /project1 is missing. Open the project and run this again.')
        return

    try:
        ui.panes.current.owner = root
    except Exception:
        pass

    old = root.op(RACK_NAME)
    if old is not None:
        old.destroy()
        print('music_rack: replaced the previous /project1/%s' % RACK_NAME)

    rack = place(root.create(baseCOMP, RACK_NAME), 200, 200)
    rack.color = (0.45, 0.28, 0.75)
    rack.viewer = True
    add_controls(rack)
    add_folder_dat(rack)
    _table, callbacks = add_callbacks(rack)
    add_readme(rack)

    player = place(rack.create(audiofileinCHOP, 'file_in'), -900, 220)
    choose(player.par.playmode, 'sequential')
    choose(player.par.repeat, 'on')
    if hasattr(player.par, 'timeslice'):
        player.par.timeslice = True
    set_expr(player, 'play', 'parent().par.Play')
    set_expr(player, 'volume', 'parent().par.Volume')
    player.viewer = True
    player.color = (0.95, 0.55, 0.2)

    speakers = place(rack.create(audiodeviceoutCHOP, 'speakers'), -560, 220)
    set_expr(speakers, 'active', 'parent().par.Play')
    if hasattr(speakers.par, 'volume'):
        speakers.par.volume = 1
    wire(speakers, player)

    mono = place(rack.create(mathCHOP, 'mono'), -900, 0)
    if hasattr(mono.par, 'chanop'):
        choose(mono.par.chanop, 'avg', 'average')
    wire(mono, player)

    spectrum = place(rack.create(audiospectrumCHOP, 'spectrum'), -560, 0)
    wire(spectrum, mono)
    spectrum.viewer = True

    filt_low = make_filter(rack, 'filt_low', 'lowpass', 140, -1250, -180)
    mid_hp = make_filter(rack, 'mid_hp', 'highpass', 180, -900, -180)
    mid_lp = make_filter(rack, 'mid_lp', 'lowpass', 2200, -900, -360)
    filt_high = make_filter(rack, 'filt_high', 'highpass', 4000, -500, -180)
    wire(filt_low, mono)
    wire(mid_hp, mono)
    wire(mid_lp, mid_hp)
    wire(filt_high, mono)

    an_low = make_analyze(rack, 'an_low', -1250, -540)
    an_mid = make_analyze(rack, 'an_mid', -900, -540)
    an_high = make_analyze(rack, 'an_high', -500, -540)
    an_rms = make_analyze(rack, 'an_rms', -150, -540)
    wire(an_low, filt_low)
    wire(an_mid, mid_lp)
    wire(an_high, filt_high)
    wire(an_rms, mono)

    gain_low = make_gain(rack, 'gain_low', 'Lowgain', -1250, -720)
    gain_mid = make_gain(rack, 'gain_mid', 'Midgain', -900, -720)
    gain_high = make_gain(rack, 'gain_high', 'Highgain', -500, -720)
    gain_rms = make_gain(rack, 'gain_rms', 'Rmsgain', -150, -720)
    wire(gain_low, an_low)
    wire(gain_mid, an_mid)
    wire(gain_high, an_high)
    wire(gain_rms, an_rms)

    lim_low = make_limit(rack, 'lim_low', -1250, -900)
    lim_mid = make_limit(rack, 'lim_mid', -900, -900)
    lim_high = make_limit(rack, 'lim_high', -500, -900)
    lim_rms = make_limit(rack, 'lim_rms', -150, -900)
    wire(lim_low, gain_low)
    wire(lim_mid, gain_mid)
    wire(lim_high, gain_high)
    wire(lim_rms, gain_rms)

    lag_low = make_lag(rack, 'lag_low', 0.02, 0.20, 'low', -1250, -1100)
    lag_mid = make_lag(rack, 'lag_mid', 0.03, 0.16, 'mid', -900, -1100)
    lag_high = make_lag(rack, 'lag_high', 0.02, 0.10, 'high', -500, -1100)
    lag_rms = make_lag(rack, 'lag_rms', 0.03, 0.18, 'rms', -150, -1100)
    wire(lag_low, lim_low)
    wire(lag_mid, lim_mid)
    wire(lag_high, lim_high)
    wire(lag_rms, lim_rms)

    kick = place(rack.create(triggerCHOP, 'kick_trigger'), -1250, -1320)
    if hasattr(kick.par, 'threshold'):
        kick.par.threshold = True
    set_expr(kick, 'threshup', 'parent().par.Kickthresh')
    if hasattr(kick.par, 'attack'):
        kick.par.attack = 0.01
    if hasattr(kick.par, 'attackunit'):
        choose(kick.par.attackunit, 'seconds')
    if hasattr(kick.par, 'peak'):
        kick.par.peak = 1
    if hasattr(kick.par, 'decay'):
        kick.par.decay = 0.02
    if hasattr(kick.par, 'sustain'):
        kick.par.sustain = 0
    if hasattr(kick.par, 'release'):
        kick.par.release = 0.12
    if hasattr(kick.par, 'releaseunit'):
        choose(kick.par.releaseunit, 'seconds')
    if hasattr(kick.par, 'retrigger'):
        kick.par.retrigger = 0.05
    if hasattr(kick.par, 'retriggerunit'):
        choose(kick.par.retriggerunit, 'seconds')
    wire(kick, lim_low)

    lag_kick = make_lag(rack, 'lag_kick', 0.0, 0.06, 'kick', -900, -1320)
    wire(lag_kick, kick)

    merged = place(rack.create(mergeCHOP, 'merge_bands'), -150, -1320)
    if hasattr(merged.par, 'srselect'):
        choose(merged.par.srselect, 'first')
    wire(merged, lag_low, 0)
    wire(merged, lag_mid, 1)
    wire(merged, lag_high, 2)
    wire(merged, lag_rms, 3)
    wire(merged, lag_kick, 4)

    audio_out = place(rack.create(nullCHOP, 'audio_out'), 180, -1320)
    if hasattr(audio_out.par, 'timeslice'):
        audio_out.par.timeslice = True
    wire(audio_out, merged)
    audio_out.viewer = True
    audio_out.color = (0.2, 0.85, 0.4)

    chop_out = place(rack.create(outCHOP, 'audio_pipe'), 460, -1320)
    wire(chop_out, audio_out)

    try:
        build_preview(rack)
    except Exception:
        print('music_rack: audio rack is built. The preview picture failed:')
        print(traceback.format_exc())

    ns = {}
    exec(CALLBACKS, ns)
    ns['reload_tracks'](rack)
    callbacks.par.active = True

    try:
        ui.panes.current.owner = rack
    except Exception:
        pass

    for node in (player, mono, audio_out, rack.op('preview')):
        if node is not None:
            try:
                node.cook(force=True)
            except Exception as err:
                print('music_rack cook:', node.path, err)
            report(node)

    print('')
    print('music_rack is ready at /project1/music_rack')
    print('Play is off. Select the component, pick a Track, set Volume, then turn Play on.')
    print('preview: loudness lights it, bass breathes it, kicks punch it, and the music sets the pace.')
    print('Save the project into C:\\Users\\James\\Desktop\\TOUCH when you want to keep it.')
    print('Channels to drive your own visuals: op(\'/project1/music_rack/audio_out\')  low, mid, high, rms, kick')


try:
    op  # noqa: B018 - TouchDesigner builtin. System Python does not have it.
except NameError:
    print('Run this inside TouchDesigner. Open the textport with Alt+T and paste:')
    print("exec(open(r'C:\\Users\\James\\Desktop\\TOUCH\\build_music_rack.py', encoding='utf-8').read())")
else:
    if __name__ != 'music_rack_lib':
        try:
            build()
        except Exception:
            print(traceback.format_exc())
            print('music_rack: the build stopped. Fix the message above and run the same line again.')
