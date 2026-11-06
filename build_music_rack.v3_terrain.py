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
        '  spec_shape    64 log-spaced spectrum bands, bass first, in a steady dB range,',
        '                plus 40 snapshots that become the terrain rows',
        'Motion scales how fast the picture moves with the music.',
        'Kick Punch scales how hard the front line flares on each kick.',
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
# against a slowly falling reference. Loud passages stay taller than quiet ones.
# It also keeps a history of snapshots for the terrain. A snapshot is taken each
# time the music clock in vis_features advances by STEP, so the terrain rushes
# in drops and nearly freezes in breakdowns.
# Output channels, all 64 samples: order (2.0 marker), h0 live, h1..h40 snapshots
# newest first, scroll (0..1 progress toward the next snapshot).
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
HISTORY = 40
STEP = 0.055        # music-clock units between snapshots

if LOG_INPUT:
    TILT = np.zeros(BANDS)
else:
    TILT = 3.0 * np.log2(np.geomspace(LO_HZ, HI_HZ, BANDS) / LO_HZ)

_s = {
    'frame': None,
    'ref': GATE_DB,
    'smooth': np.zeros(BANDS),
    'edges': None,
    'count': 0,
    'history': [np.zeros(BANDS) for _ in range(HISTORY)],
    'last_push': None,
    'own_clock': 0.0,
}


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
    level = np.clip((bands - (_s['ref'] - RANGE_DB)) / RANGE_DB, 0.0, 1.0)
    # Soften neighbouring bands so ridges read as curves, not spikes.
    for _ in range(2):
        padded = np.concatenate(([level[0]], level, [level[-1]]))
        level = padded[:-2] * 0.25 + padded[1:-1] * 0.5 + padded[2:] * 0.25
    return level


def _music_time(scriptOp, dt):
    feat = scriptOp.parent().op('vis_features')
    if feat is not None:
        chan = feat.chan('time')
        if chan is not None:
            return float(chan[0])
    _s['own_clock'] += dt * 0.5
    return _s['own_clock']


def _fill(chan, row):
    values = [float(v) for v in row]
    try:
        chan.vals = values
    except Exception:
        for i, v in enumerate(values):
            chan[i] = v


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

    now = _music_time(scriptOp, dt)
    if _s['last_push'] is None or now < _s['last_push']:
        _s['last_push'] = now
    if now - _s['last_push'] > STEP * HISTORY:
        _s['last_push'] = now - STEP * HISTORY
    while now - _s['last_push'] >= STEP:
        _s['history'].insert(0, _s['smooth'].copy())
        _s['history'].pop()
        _s['last_push'] += STEP
    scroll = min(1.0, max(0.0, (now - _s['last_push']) / STEP))

    rows = [('order', np.full(BANDS, 2.0)), ('h0', _s['smooth'])]
    rows += [('h%d' % (i + 1), row) for i, row in enumerate(_s['history'])]
    rows.append(('scroll', np.full(BANDS, scroll)))
    scriptOp.clear()
    scriptOp.numSamples = BANDS
    for name, row in rows:
        _fill(scriptOp.appendChan(name), row)
    return
'''


VISUAL_SHADER = r'''
layout(location = 0) out vec4 fragColor;
uniform float uTime;    // music clock from vis_features
uniform float uPunch;   // Kick Punch slider
uniform float uClock;   // wall clock, for grain and star twinkle only

// Input 0, one row from vis_features:
//   0 low, 1 mid, 2 high, 3 rms, 4 kick, 5 section, 6 flux
// Input 1, from spec_shape: 64 bands wide, bass first. Rows: order marker (2.0),
//   live spectrum, 40 snapshots newest first, scroll fraction.

const int HIST = 41;            // live row + 40 snapshots
const float CAM = 0.55;         // how far below the horizon the front row sits
const float DZ = 0.16;          // depth step between rows
const float SPREAD = 1.35;      // world units per screen height at the front row
const float HEIGHT = 0.48;      // peak height of the front row, in screen heights
const float PX = 1.0 / 720.0;

int gRows = 0;
int gBands = 0;
bool gFlip = false;

float feature(int i)
{
    ivec2 s = textureSize(sTD2DInputs[0], 0);
    if (s.x >= s.y) {
        return i < s.x ? texelFetch(sTD2DInputs[0], ivec2(i, 0), 0).r : 0.0;
    }
    return i < s.y ? texelFetch(sTD2DInputs[0], ivec2(0, i), 0).r : 0.0;
}

// Row r of spec_shape, whichever way up CHOP to TOP stacked the channels.
float cell(int x, int r)
{
    int y = gFlip ? (gRows - 1 - r) : r;
    return texelFetch(sTD2DInputs[1], ivec2(x, y), 0).r;
}

void readLayout()
{
    ivec2 s = textureSize(sTD2DInputs[1], 0);
    gBands = s.x;
    gRows = s.y;
    gFlip = gRows > 1 && abs(texelFetch(sTD2DInputs[1], ivec2(0, 0), 0).r - 2.0) > 0.5;
}

// Height of history row k (0 = live) at world x. Bass in the middle, treble out to |x| = 1.
float ridge(int k, float wx)
{
    float u = abs(wx);
    if (u >= 1.0 || gBands < 2 || k + 1 >= gRows) {
        return 0.0;
    }
    float x = u * float(gBands - 1);
    int i0 = int(floor(x));
    int i1 = min(i0 + 1, gBands - 1);
    float v = mix(cell(i0, k + 1), cell(i1, k + 1), x - float(i0));
    return pow(clamp(v, 0.0, 1.0), 1.35) * (1.0 - smoothstep(0.8, 1.0, u));
}

float segDist(vec2 p, vec2 a, vec2 b)
{
    vec2 ab = b - a;
    float h = clamp(dot(p - a, ab) / max(dot(ab, ab), 1e-9), 0.0, 1.0);
    return length(p - a - ab * h);
}

float hash21(vec2 p)
{
    p = fract(p * vec2(123.34, 345.45));
    p += dot(p, p + 34.345);
    return fract(p.x * p.y);
}

// Two-colour looks, quiet to loud: ice, mint/violet, pink/blue, amber/red.
// a is the near colour, b the far colour.
void duo(float s, out vec3 a, out vec3 b)
{
    vec3 A[4] = vec3[4](
        vec3(0.92, 0.95, 1.00), vec3(0.30, 1.00, 0.82),
        vec3(1.00, 0.24, 0.58), vec3(1.00, 0.62, 0.18));
    vec3 B[4] = vec3[4](
        vec3(0.25, 0.50, 1.00), vec3(0.40, 0.28, 1.00),
        vec3(0.22, 0.42, 1.00), vec3(0.92, 0.16, 0.30));
    float x = clamp(s, 0.0, 1.0) * 3.0;
    int i = int(min(floor(x), 2.0));
    float f = smoothstep(0.35, 0.65, x - float(i));
    a = mix(A[i], A[i + 1], f);
    b = mix(B[i], B[i + 1], f);
}

void main()
{
    readLayout();
    float t = uTime;
    vec2 uv = vUV.st;
    float low = clamp(feature(0), 0.0, 1.0);
    float mid = clamp(feature(1), 0.0, 1.0);
    float high = clamp(feature(2), 0.0, 1.0);
    float rms = clamp(feature(3), 0.0, 1.0);
    float kick = clamp(feature(4), 0.0, 1.0);
    float section = clamp(feature(5), 0.0, 1.0);
    float punch = kick * uPunch;
    float scroll = gRows > 0 ? clamp(cell(0, gRows - 1), 0.0, 1.0) : 0.0;

    vec3 cA;
    vec3 cB;
    duo(section, cA, cB);

    vec2 p = vec2((uv.x - 0.5) * 1.7778, uv.y);
    float sway = sin(t * 0.11) * 0.08;
    float horizon = 0.64 + punch * 0.012;   // kicks dip the camera a touch

    // Sky: near black, a haze on the horizon that the bass lights.
    vec3 sky = vec3(0.004, 0.004, 0.008);
    sky += cB * exp(-abs(p.y - horizon) * 9.0) * (0.03 + low * 0.12);

    // Sparse stars. Tiny next to their cells, so nothing gets clipped.
    vec2 sg = (p + vec2(sway * 0.3, 0.0)) * 60.0;
    vec2 sid = floor(sg);
    float sh = hash21(sid);
    if (sh > 0.93) {
        vec2 off = (vec2(hash21(sid + 3.1), hash21(sid + 7.7)) - 0.5) * 0.6;
        float d = length(fract(sg) - 0.5 - off);
        float tw = 0.5 + 0.5 * sin(uClock * (1.5 + sh * 3.0) + sh * 40.0);
        sky += mix(cA, vec3(1.0), 0.6) * (1.0 - smoothstep(0.0, 0.15, d)) * tw
            * (0.2 + high * 1.2) * smoothstep(horizon, horizon + 0.15, p.y);
    }

    // Terrain, front to back. Each ridge's black fill hides the rows behind it.
    vec3 lines = vec3(0.0);
    vec3 fill = vec3(0.0);
    bool hidden = false;
    for (int k = 0; k < HIST; k++) {
        float z = (k == 0) ? 1.0 : 1.0 + (float(k) + scroll) * DZ;
        float fog = exp(-(z - 1.0) * 0.55);
        float base = horizon - CAM / z;
        float scale = z * SPREAD;
        float wx = (p.x + sway) * scale;
        // Distance to the two short segments either side of this pixel, so
        // steep peaks keep a thin line instead of smearing up the column.
        float dx = 2.0 * PX;
        float hs = HEIGHT / z;
        float yl = base + ridge(k, wx - dx * scale) * hs;
        float y0 = base + ridge(k, wx) * hs;
        float yr = base + ridge(k, wx + dx * scale) * hs;
        vec2 here = vec2(p.x, p.y);
        float dist = min(
            segDist(here, vec2(p.x - dx, yl), vec2(p.x, y0)),
            segDist(here, vec2(p.x, y0), vec2(p.x + dx, yr)));
        float d = p.y < y0 ? -dist : dist;

        float front = (k == 0) ? 1.0 : 0.0;
        float w = PX * (0.9 + front * (0.8 + punch * 1.6));
        float core = 1.0 - smoothstep(w, w + PX, abs(d));
        float halo = exp(-abs(d) / (PX * (5.0 + front * 6.0 + mid * 4.0)));
        vec3 lc = mix(cA, cB, clamp((z - 1.0) / 2.5, 0.0, 1.0));
        float bright = fog * (0.45 + rms * 0.45) * (1.0 + front * (0.5 + punch * 1.2));
        lines += lc * (core + halo * 0.22) * bright;

        if (d < 0.0) {
            hidden = true;
            fill = lc * fog * 0.05 * exp(d / 0.04) * (0.3 + low);
            break;
        }
    }

    vec3 col = (hidden ? fill : sky) + lines * (1.0 + punch * 0.3);

    vec2 vq = uv - 0.5;
    col *= 1.0 - dot(vq, vq) * 0.9;
    col = 1.0 - exp(-max(col, 0.0) * 1.4);
    float grain = hash21(uv * vec2(1280.0, 720.0) + fract(uClock * 7.13) * 100.0) - 0.5;
    col += grain * 0.018;
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
    """Replace the picture with the neon spectrum terrain.

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
        ('uClock', 'absTime.seconds'),
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
    print('A neon spectrum terrain: the front line is the live spectrum (bass in the middle),')
    print('older moments recede toward the horizon. It rushes in loud sections and nearly')
    print('freezes in quiet ones. Kicks flare the front line; colour follows the section.')
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
    print('preview is a neon spectrum terrain that scrolls with the music. Kicks flare the front line.')
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
