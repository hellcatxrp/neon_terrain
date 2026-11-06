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
        '  cycle_sim     the light cycle: steering, trail, crashes, camera',
        '  cycle_arena   where the trail lies on the arena floor (for the shader)',
        '  cycle_hist    spectrum snapshots along the trail, plus the cycle state row',
        'Motion scales how fast the cycle drives with the music.',
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

# Script CHOP: the live spectrum as 64 log-spaced bands, 0..1, bass first.
# Converted to dB, tilted +3 dB per octave so treble is not buried, and scaled
# against a slowly falling reference. Loud passages stay taller than quiet ones.
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
    level = np.clip((bands - (_s['ref'] - RANGE_DB)) / RANGE_DB, 0.0, 1.0)
    # Soften neighbouring bands so ridges read as curves, not spikes.
    for _ in range(2):
        padded = np.concatenate(([level[0]], level, [level[-1]]))
        level = padded[:-2] * 0.25 + padded[1:-1] * 0.5 + padded[2:] * 0.25
    return level


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
    values = [float(v) for v in _s['smooth']]
    try:
        chan.vals = values
    except Exception:
        for i, v in enumerate(values):
            chan[i] = v
    return
'''


# Text DAT module: the light cycle. Both Script TOPs call step() each frame;
# the first call in a frame does the work. Floor coordinates are (x, z) with
# the arena spanning -ARENA/2..ARENA/2 on both axes.
#
#   S['arena']  GRID x GRID x 4. R = trail position s (-1 empty), G = across (-1..1).
#   S['hist']   (CAP + 1) x 64 x 4. Row s % CAP holds the spectrum at trail position s.
#               Row CAP is the state row the shader reads (camera, head, crash).
#   Both carry A = 7 at [0, 0] so the shader can tell which way up TouchDesigner put them.
CYCLE_SIM = r'''
import math
import numpy as np

ARENA = 44.0          # arena side, world units
GRID = 640            # arena texture resolution
HALF = 1.6            # ribbon half-width
SPACING = 0.16        # world distance between spectrum snapshots
STEP = 0.055          # music-clock units per snapshot
CAP = 2048            # snapshots kept; older trail fades away
BANDS = 64
HEIGHT = 1.3          # ribbon peak height
RADIUS = 3.0          # tightest turn radius
WALL = 2.4            # arena wall height
SAFE = 24             # rows behind the head that never count as a crash
CRASH_SECONDS = 3.2
FLY_DOWN = 1.6        # seconds to drop from the overhead view into the chase
LEAD_AHEAD = 6.0      # camera rides ahead of the cycle...
LEAD_SIDE = 3.0       # ...off to one side...
LEAD_UP = 3.4         # ...and above it, looking back along the trail
LOOK_BACK = 3.0
QUARTER = math.pi / 2
PIX = ARENA / GRID

S = {}


def _ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3.0 - 2.0 * x)


def _dir(theta):
    return np.array([math.cos(theta), math.sin(theta)])


def _left(theta):
    return np.array([-math.sin(theta), math.cos(theta)])


def init():
    S.clear()
    S['rng'] = np.random.default_rng()
    S['arena'] = np.zeros((GRID, GRID, 4), np.float32)
    S['hist'] = np.zeros((CAP + 1, BANDS, 4), np.float32)
    S['frame'] = None
    S['clock'] = 0.0
    S['music'] = None
    S['kick_prev'] = 0.0
    S['kick'] = 0.0
    S['crashes'] = 0
    respawn()


def _wall_room(pos, theta):
    d = _dir(theta)
    room = 1e9
    for axis in (0, 1):
        if abs(d[axis]) > 1e-6:
            edge = ARENA / 2 if d[axis] > 0 else -ARENA / 2
            room = min(room, (edge - pos[axis]) / d[axis])
    return room


def respawn():
    arena = S['arena']
    arena[...] = 0.0
    arena[..., 0] = -1.0
    arena[0, 0, 3] = 7.0
    hist = S['hist']
    hist[...] = 0.0
    hist[0, 0, 3] = 7.0
    rng = S['rng']
    pos = rng.uniform(-ARENA * 0.22, ARENA * 0.22, 2)
    best = max(range(4), key=lambda k: _wall_room(pos, k * QUARTER))
    theta = best * QUARTER
    S.update(
        pos=pos, theta=theta, s=0.0, mode='straight', turn_sign=0, turned=0.0,
        straight=0.0, min_len=rng.uniform(2.5, 6.0), max_len=rng.uniform(8.0, 15.0),
        crash_t=0.0, crash_pos=pos.copy(), since_spawn=0.0, live_row=0,
        cam_yaw=theta, run_start=None)


def _cell(q):
    ix = int((q[0] + ARENA / 2) / PIX)
    iy = int((q[1] + ARENA / 2) / PIX)
    if ix < 0 or iy < 0 or ix >= GRID or iy >= GRID:
        return None
    return iy, ix


def _blocked(q):
    lim = ARENA / 2 - 0.15
    if abs(q[0]) > lim or abs(q[1]) > lim:
        return True
    cell = _cell(q)
    if cell is None:
        return True
    s = S['arena'][cell[0], cell[1], 0]
    return s >= 0.0 and S['s'] - CAP <= s < S['s'] - SAFE


def _blocked_band(centre, theta):
    side = _left(theta) * HALF
    for k in (-0.85, 0.0, 0.85):
        if _blocked(centre + side * k):
            return True
    return False


def _free(origin, theta, limit):
    d = _dir(theta)
    dist = 0.0
    while dist < limit:
        dist += 0.35
        if _blocked_band(origin + d * dist, theta):
            return dist
    return limit


def _turn_rate(turned):
    # Eases in and out of each quarter turn; never tighter than RADIUS.
    return 0.45 + 0.55 * math.sin(math.pi * min(turned / QUARTER, 1.0))


def _arc(pos, theta, sign, step=0.25):
    # The exact path _steer drives through a quarter turn.
    points = []
    turned = 0.0
    while turned < QUARTER - 1e-6:
        d = min(step / RADIUS * _turn_rate(turned), QUARTER - turned)
        theta += sign * d
        turned += d
        pos = pos + _dir(theta) * step
        points.append((pos, theta))
    return points


FORWARD = max(p[0] for p, _t in _arc(np.zeros(2), 0.0, 1))   # how far ahead a turn reaches


def _turn_room(sign):
    # Free distance after a quarter turn to this side; 0 if the arc itself is blocked.
    points = _arc(S['pos'], S['theta'], sign)
    for pos, theta in points[1::2]:
        if _blocked_band(pos + _dir(theta) * 0.4, theta):
            return 0.0
    end, theta = points[-1]
    return FORWARD * 0.5 + _free(end, theta, 14.0)


def _steer(dist, kick_edge):
    rng = S['rng']
    if S['mode'] == 'straight':
        S['straight'] += dist
        ahead = _free(S['pos'], S['theta'], FORWARD + HALF + 4.0)
        need = ahead < FORWARD + HALF + 0.8
        want = S['straight'] > S['min_len'] and (kick_edge or S['straight'] > S['max_len'])
        if not (need or want):
            return
        left = _turn_room(1)
        right = _turn_room(-1)
        if not need and max(left, right) < 4.0:
            S['straight'] = 0.0   # nowhere better to go yet; keep straight a while
            return
        if need or min(left, right) < 3.0:
            sign = 1 if left >= right else -1
        else:
            p_left = left * left / (left * left + right * right)
            sign = 1 if rng.random() < p_left else -1
        S.update(mode='turn', turn_sign=sign, turned=0.0)
        return
    step = min(dist / RADIUS * _turn_rate(S['turned']), QUARTER - S['turned'])
    S['theta'] += S['turn_sign'] * step
    S['turned'] += step
    if S['turned'] >= QUARTER - 1e-6:
        S['theta'] = round(S['theta'] / QUARTER) * QUARTER
        S.update(mode='straight', straight=0.0,
                 min_len=rng.uniform(2.5, 6.0), max_len=rng.uniform(8.0, 15.0))


def _paint(p0, p1, s0, s1, theta):
    arena = S['arena']
    seg = p1 - p0
    length = float(np.hypot(seg[0], seg[1]))
    d = seg / length if length > 1e-6 else _dir(theta)
    n = np.array([-d[1], d[0]])
    ext = PIX * 1.5
    corners = [p0 - d * ext + n * HALF, p0 - d * ext - n * HALF,
               p1 + d * ext + n * HALF, p1 + d * ext - n * HALF]
    xs = [c[0] for c in corners]
    zs = [c[1] for c in corners]
    ix0 = max(0, int((min(xs) + ARENA / 2) / PIX) - 1)
    ix1 = min(GRID, int((max(xs) + ARENA / 2) / PIX) + 2)
    iy0 = max(0, int((min(zs) + ARENA / 2) / PIX) - 1)
    iy1 = min(GRID, int((max(zs) + ARENA / 2) / PIX) + 2)
    if ix0 >= ix1 or iy0 >= iy1:
        return
    wx = (np.arange(ix0, ix1) + 0.5) * PIX - ARENA / 2
    wz = (np.arange(iy0, iy1) + 0.5) * PIX - ARENA / 2
    X, Z = np.meshgrid(wx - p0[0], wz - p0[1])
    along = X * d[0] + Z * d[1]
    across = X * n[0] + Z * n[1]
    mask = (along >= -ext) & (along <= length + ext) & (np.abs(across) <= HALF)
    if length > 1e-6:
        s = s0 + along / length * (s1 - s0)
    else:
        s = np.full_like(along, s1)
    region = arena[iy0:iy1, ix0:ix1]
    old = region[..., 0]
    recent = 2.0 * HALF / SPACING + 4.0
    mask &= (old < 0.0) | (old >= s1 - recent) | (old < s1 - CAP)
    region[..., 0][mask] = s[mask]
    region[..., 1][mask] = across[mask] / HALF


def _drive(rows, kick_edge):
    dist = rows * SPACING
    if dist <= 0.0:
        return
    count = max(1, int(math.ceil(dist / 0.08)))
    sub = dist / count
    sub_rows = rows / count
    for _ in range(count):
        p0 = S['pos'].copy()
        s0 = S['s']
        _steer(sub, kick_edge)
        kick_edge = False
        S['pos'] = p0 + _dir(S['theta']) * sub
        S['s'] = s0 + sub_rows
        _paint(p0, S['pos'], s0, S['s'], S['theta'])
        if _blocked_band(S['pos'] + _dir(S['theta']) * 0.15, S['theta']):
            S.update(mode='crash', crash_t=0.0, crash_pos=S['pos'].copy())
            S['crashes'] += 1
            return


def _write_live(live):
    hist = S['hist']
    k = int(math.floor(S['s'])) + 1
    start = min(S['live_row'], k)
    if k - start > CAP:
        start = k - CAP
    for row in range(start, k + 1):
        hist[row % CAP, :, 0] = live
    S['live_row'] = k


def _camera(dt):
    diff = (S['theta'] - S['cam_yaw'] + math.pi) % (2 * math.pi) - math.pi
    S['cam_yaw'] += diff * (1.0 - math.exp(-dt / 0.45))
    f = _dir(S['cam_yaw'])
    n = _left(S['cam_yaw'])
    head = S['pos']
    bob = S['kick'] * 0.12
    lead = head + f * LEAD_AHEAD - n * LEAD_SIDE
    look = head - f * LOOK_BACK
    chase_pos = np.array([lead[0], LEAD_UP - bob, lead[1]])
    chase_tgt = np.array([look[0], 0.2, look[1]])
    orbit = S['clock'] * 0.12
    over_pos = np.array([math.sin(orbit) * ARENA * 0.45, ARENA * 0.85, math.cos(orbit) * ARENA * 0.45])
    crashed = S['mode'] == 'crash'
    focus = S['crash_pos'] if crashed else head
    over_tgt = np.array([focus[0] * 0.35, 0.0, focus[1] * 0.35])
    if crashed:
        blend = _ease(S['crash_t'] / 0.9)
    else:
        blend = 1.0 - _ease(S['since_spawn'] / FLY_DOWN)
    S['cam_pos'] = chase_pos + (over_pos - chase_pos) * blend
    S['cam_tgt'] = chase_tgt + (over_tgt - chase_tgt) * blend


def _write_state():
    st = np.zeros(BANDS, np.float32)
    st[0:3] = S['cam_pos']
    st[3:6] = S['cam_tgt']
    st[6] = S['s']
    st[7] = max(1e-3, S['crash_t'] / CRASH_SECONDS) if S['mode'] == 'crash' else 0.0
    st[8], st[9] = S['crash_pos']
    st[10], st[11] = S['pos']
    st[12] = CAP
    st[13] = ARENA
    st[14] = HALF
    st[15] = HEIGHT
    st[16], st[17] = _dir(S['theta'])
    st[18] = WALL
    st[19] = CRASH_SECONDS
    st[20] = SPACING
    S['hist'][CAP, :, 0] = st


def _features(rack):
    out = {}
    node = rack.op('vis_features')
    if node is not None:
        for name in ('time', 'kick'):
            chan = node.chan(name)
            if chan is not None:
                out[name] = float(chan[0])
    return out


def _live_spectrum(rack):
    node = rack.op('spec_shape')
    if node is None or node.numChans < 1 or node.numSamples < 2:
        return np.zeros(BANDS, np.float32)
    vals = np.asarray(node[0].numpyArray(), dtype=np.float32)
    if vals.shape[0] != BANDS:
        vals = np.interp(np.linspace(0, 1, BANDS), np.linspace(0, 1, vals.shape[0]), vals)
    return vals


def step(rack, frame, rate):
    if not S:
        init()
    last = S['frame']
    if last is not None and frame == last:
        return
    if last is None or frame < last:
        dt = 1.0 / 60.0
    else:
        dt = (frame - last) / float(rate or 60)
    dt = min(dt, 0.1)
    S['frame'] = frame
    S['clock'] += dt

    feats = _features(rack)
    music = feats.get('time', S['clock'] * 0.5)
    if S['music'] is None:
        S['music'] = music
    dmusic = max(0.0, music - S['music'])
    S['music'] = music
    kick = feats.get('kick', 0.0)
    kick_edge = kick > S['kick_prev'] + 0.3
    S['kick_prev'] = kick
    S['kick'] = kick

    if S['mode'] == 'crash':
        S['crash_t'] += dt
        if S['crash_t'] >= CRASH_SECONDS:
            respawn()
    else:
        S['since_spawn'] += dt
        _drive(dmusic / STEP, kick_edge)
        _write_live(_live_spectrum(rack))
    _camera(dt)
    _write_state()
'''

# Script TOP: hands one of cycle_sim's arrays to the GPU every frame.
CYCLE_TOP_CALLBACKS = r'''
WHICH = '__WHICH__'


def onSetupParameters(scriptOp):
    return


def onPulse(par):
    return


def onCook(scriptOp):
    rack = scriptOp.parent()
    sim = rack.op('cycle_sim').module
    sim.step(rack, absTime.frame, project.cookRate)
    scriptOp.copyNumpyArray(sim.S[WHICH])
    return
'''


VISUAL_SHADER = r'''
layout(location = 0) out vec4 fragColor;
uniform float uPunch;   // Kick Punch slider
uniform float uClock;   // wall clock, for grain and star twinkle only

// Input 0, one row from vis_features: 0 low, 1 mid, 2 high, 3 rms, 4 kick, 5 section.
// Input 1, cycle_arena: R = trail position s (-1 empty), G = across (-1..1).
// Input 2, cycle_hist: rows 0..CAP-1 are spectrum snapshots (64 wide, bass first),
//   the last row is the state row written by cycle_sim.
// Both cycle textures carry A = 7 at texel (0, 0) when they are the right way up.

const float FOCAL = 1.6;
const int MARCH = 160;
const int SPARKS = 48;

ivec2 gArenaSize;
bool gArenaFlip;
ivec2 gHistSize;
bool gHistFlip;
int gCap;
int gBands;
vec3 gCam;
vec3 gTgt;
float gHead;
float gCrash;
vec2 gCrashPos;
vec2 gHeadPos;
float gArena;
float gHalf;
float gHeight;
float gWall;
float gCrashSeconds;
float gCollapse;

float feature(int i)
{
    ivec2 s = textureSize(sTD2DInputs[0], 0);
    if (s.x >= s.y) {
        return i < s.x ? texelFetch(sTD2DInputs[0], ivec2(i, 0), 0).r : 0.0;
    }
    return i < s.y ? texelFetch(sTD2DInputs[0], ivec2(0, i), 0).r : 0.0;
}

float histTexel(int x, int row)
{
    int y = gHistFlip ? (gHistSize.y - 1 - row) : row;
    return texelFetch(sTD2DInputs[2], ivec2(x, y), 0).r;
}

vec2 arenaTexel(ivec2 c)
{
    c = clamp(c, ivec2(0), gArenaSize - 1);
    if (gArenaFlip) {
        c.y = gArenaSize.y - 1 - c.y;
    }
    return texelFetch(sTD2DInputs[1], c, 0).rg;
}

void readState()
{
    gHistSize = textureSize(sTD2DInputs[2], 0);
    gHistFlip = texelFetch(sTD2DInputs[2], ivec2(0, 0), 0).a < 6.0;
    gArenaSize = textureSize(sTD2DInputs[1], 0);
    gArenaFlip = texelFetch(sTD2DInputs[1], ivec2(0, 0), 0).a < 6.0;
    gBands = gHistSize.x;
    int r = gHistSize.y - 1;
    gCam = vec3(histTexel(0, r), histTexel(1, r), histTexel(2, r));
    gTgt = vec3(histTexel(3, r), histTexel(4, r), histTexel(5, r));
    gHead = histTexel(6, r);
    gCrash = histTexel(7, r);
    gCrashPos = vec2(histTexel(8, r), histTexel(9, r));
    gHeadPos = vec2(histTexel(10, r), histTexel(11, r));
    gCap = max(int(histTexel(12, r) + 0.5), 1);
    gArena = max(histTexel(13, r), 1.0);
    gHalf = histTexel(14, r);
    gHeight = histTexel(15, r);
    gWall = histTexel(18, r);
    gCrashSeconds = max(histTexel(19, r), 0.1);
    gCollapse = 1.0 - smoothstep(0.2, 0.85, gCrash);
}

float specRow(int row, float u)
{
    int r = row % gCap;
    if (r < 0) {
        r += gCap;
    }
    float x = u * float(gBands - 1);
    int i0 = int(x);
    int i1 = min(i0 + 1, gBands - 1);
    return mix(histTexel(i0, r), histTexel(i1, r), x - float(i0));
}

// Ribbon height at trail position s and across position a. Bass in the middle.
float profile(float s, float a)
{
    float u = clamp(abs(a), 0.0, 1.0);
    int k = int(floor(s));
    float v = mix(specRow(k, u), specRow(k + 1, u), fract(s));
    return pow(clamp(v, 0.0, 1.0), 1.35) * (1.0 - smoothstep(0.8, 1.0, u));
}

float validS(float s)
{
    return (s >= 0.0 && s > gHead - float(gCap) && s <= gHead + 3.0) ? 1.0 : 0.0;
}

// Trail under a floor point: returns coverage 0..1 and writes s and a.
float trailAt(vec2 xz, out float s, out float a)
{
    vec2 f = (xz + 0.5 * gArena) / gArena * vec2(gArenaSize) - 0.5;
    ivec2 i = ivec2(floor(f));
    vec2 w = f - vec2(i);
    vec2 t00 = arenaTexel(i);
    vec2 t10 = arenaTexel(i + ivec2(1, 0));
    vec2 t01 = arenaTexel(i + ivec2(0, 1));
    vec2 t11 = arenaTexel(i + ivec2(1, 1));
    float w00 = (1.0 - w.x) * (1.0 - w.y) * validS(t00.x);
    float w10 = w.x * (1.0 - w.y) * validS(t10.x);
    float w01 = (1.0 - w.x) * w.y * validS(t01.x);
    float w11 = w.x * w.y * validS(t11.x);
    float total = w00 + w10 + w01 + w11;
    s = -1.0;
    a = 0.0;
    if (total < 1e-4) {
        return 0.0;
    }
    float lo = min(min(w00 > 0.0 ? t00.x : 1e9, w10 > 0.0 ? t10.x : 1e9),
                   min(w01 > 0.0 ? t01.x : 1e9, w11 > 0.0 ? t11.x : 1e9));
    float hi = max(max(w00 > 0.0 ? t00.x : -1e9, w10 > 0.0 ? t10.x : -1e9),
                   max(w01 > 0.0 ? t01.x : -1e9, w11 > 0.0 ? t11.x : -1e9));
    if (hi - lo > 6.0) {
        // Two passes of the trail side by side: take one, do not blend them.
        vec4 ws = vec4(w00, w10, w01, w11);
        float m = max(max(ws.x, ws.y), max(ws.z, ws.w));
        vec2 pick = ws.x == m ? t00 : (ws.y == m ? t10 : (ws.z == m ? t01 : t11));
        s = pick.x;
        a = pick.y;
        return m / total;
    }
    s = (w00 * t00.x + w10 * t10.x + w01 * t01.x + w11 * t11.x) / total;
    a = (w00 * t00.y + w10 * t10.y + w01 * t01.y + w11 * t11.y) / total;
    return total;
}

float terrainHeight(vec2 xz, out float s, out float a)
{
    float cover = trailAt(xz, s, a);
    if (cover <= 0.0) {
        return 0.0;
    }
    return profile(s, a) * gHeight * gCollapse * cover;
}

float hash21(vec2 p)
{
    p = fract(p * vec2(123.34, 345.45));
    p += dot(p, p + 34.345);
    return fract(p.x * p.y);
}

// Two-colour looks, quiet to loud: ice, mint/violet, pink/blue, amber/red.
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

// Ray against the arena's floor square: entry and exit distances.
vec2 arenaSpan(vec3 ro, vec3 rd)
{
    float h = 0.5 * gArena;
    vec2 inv = 1.0 / vec2(abs(rd.x) > 1e-6 ? rd.x : 1e-6, abs(rd.z) > 1e-6 ? rd.z : 1e-6);
    vec2 t0 = (vec2(-h) - ro.xz) * inv;
    vec2 t1 = (vec2(h) - ro.xz) * inv;
    vec2 tn = min(t0, t1);
    vec2 tf = max(t0, t1);
    return vec2(max(tn.x, tn.y), min(tf.x, tf.y));
}

// What the ray hits. kind: 0 nothing, 1 ribbon, 2 floor.
void trace(vec3 ro, vec3 rd, out int kind, out float tHit, out float sHit, out float aHit, out float hHit)
{
    kind = 0;
    tHit = 1e9;
    sHit = 0.0;
    aHit = 0.0;
    hHit = 0.0;
    vec2 span = arenaSpan(ro, rd);
    float hmax = gHeight * 1.02 * gCollapse + 0.001;
    float tTop = 0.0;
    float tFloor = 1e9;
    if (rd.y < -1e-5) {
        tTop = max((ro.y - hmax) / -rd.y, 0.0);
        tFloor = ro.y / -rd.y;
    } else if (ro.y > hmax) {
        tTop = 1e9;
    }
    float t0 = max(max(span.x, 0.0), tTop);
    float t1 = min(span.y, tFloor);
    if (span.x < span.y && t0 < t1) {
        float slab = t1 - t0;
        float maxStep = max(slab / 24.0, 0.02);
        float t = t0;
        float tPrev = t0;
        bool hit = false;
        for (int i = 0; i < MARCH; i++) {
            vec3 p = ro + rd * t;
            float s;
            float a;
            float h = terrainHeight(p.xz, s, a);
            if (p.y <= h + 1e-4) {
                hit = true;
                break;
            }
            if (t >= t1) {
                break;
            }
            tPrev = t;
            t = min(t + min(max(t * 0.012, 0.02), maxStep), t1);
        }
        if (hit) {
            float lo = tPrev;
            float hi = t;
            for (int j = 0; j < 6; j++) {
                float mid = 0.5 * (lo + hi);
                vec3 p = ro + rd * mid;
                float s;
                float a;
                if (p.y <= terrainHeight(p.xz, s, a)) {
                    hi = mid;
                } else {
                    lo = mid;
                }
            }
            tHit = hi;
            vec3 p = ro + rd * tHit;
            float s;
            float a;
            float cover = trailAt(p.xz, s, a);
            if (cover > 0.3) {
                kind = 1;
                sHit = s;
                aHit = a;
                hHit = profile(s, a) * gCollapse;
            } else {
                kind = 2;
            }
            return;
        }
    }
    if (rd.y < -1e-5) {
        kind = 2;
        tHit = ro.y / -rd.y;
    }
}

vec2 project(vec3 p, vec3 ro, vec3 fw, vec3 rt, vec3 up, out float depth)
{
    vec3 v = p - ro;
    depth = dot(v, fw);
    return vec2(dot(v, rt), dot(v, up)) / max(depth, 1e-3) * FOCAL;
}

void main()
{
    readState();
    vec2 uv = vUV.st;
    float low = clamp(feature(0), 0.0, 1.0);
    float mid = clamp(feature(1), 0.0, 1.0);
    float high = clamp(feature(2), 0.0, 1.0);
    float rms = clamp(feature(3), 0.0, 1.0);
    float kick = clamp(feature(4), 0.0, 1.0);
    float section = clamp(feature(5), 0.0, 1.0);
    float punch = kick * uPunch;
    vec3 cA;
    vec3 cB;
    duo(section, cA, cB);

    vec3 ro = gCam;
    vec3 fw = gTgt - gCam;
    bool ready = dot(fw, fw) > 1e-6;
    fw = ready ? normalize(fw) : vec3(0.0, 0.0, 1.0);
    vec3 rt = normalize(cross(fw, vec3(0.0, 1.0, 0.0)));
    vec3 up = cross(rt, fw);
    vec2 sc = vec2((uv.x - 0.5) * 1.7778, uv.y - 0.5);
    vec3 rd = normalize(fw * FOCAL + rt * sc.x + up * sc.y);

    int kind;
    float tHit;
    float s;
    float a;
    float h;
    trace(ro, rd, kind, tHit, s, a, h);

    // Derivatives in uniform control flow.
    float fwS = fwidth(s);
    float fwA = fwidth(a);

    vec3 hp = ro + rd * min(tHit, 400.0);
    float fog = exp(-min(tHit, 400.0) * 0.03);
    float pix = min(tHit, 400.0) / (720.0 * FOCAL);
    vec3 col;

    if (kind == 1) {
        float age = gHead - s;
        float near1 = 1.0 - smoothstep(0.35, 0.75, fwS);
        float d1 = abs(fract(s + 0.5) - 0.5);
        float l1 = (1.0 - smoothstep(0.5 * fwS, 1.5 * fwS, d1)) * near1;
        float d8 = abs(fract(s / 8.0 + 0.5) - 0.5) * 8.0;
        float l8 = (1.0 - smoothstep(0.5 * fwS, 1.5 * fwS, d8)) * (1.0 - near1)
            * (1.0 - smoothstep(3.0, 6.0, fwS));
        float halo = exp(-d1 / max(fwS * 2.0, 0.03)) * near1 * 0.22;
        float ea = abs(abs(a) - 0.96);
        float rail = (1.0 - smoothstep(0.5 * fwA, 1.5 * fwA, ea)) * 0.6 * step(fwA, 0.5);
        float guard = step(fwS, 6.0);
        float fd = gHead - s;
        float front = (1.0 - smoothstep(0.0, 1.2 + fwS * 2.0, fd)) * step(-0.5, fd);
        vec3 lc = mix(cA, cB, smoothstep(0.0, 90.0, age));
        float derez = smoothstep(0.12, 0.7, gCrash);
        float keep = step(derez, hash21(vec2(floor(s / 3.0), floor(a * 3.0 + 3.0))));
        float bright = (0.45 + rms * 0.45) * (0.55 + h * 0.9) * fog;
        col = lc * (l1 + l8 + halo + rail) * bright * keep * guard;
        col += mix(lc, vec3(1.0), 0.5) * front * (1.2 + punch * 2.0) * fog * keep * guard;
        col += lc * 0.03 * fog * (0.3 + low);
    } else if (kind == 2) {
        vec2 g = abs(fract(hp.xz / 2.0 + 0.5) - 0.5) * 2.0;
        float gl = (1.0 - smoothstep(pix * 0.8, pix * 2.0, min(g.x, g.y)))
            * (1.0 - smoothstep(0.08, 0.3, pix));
        float inside = (abs(hp.x) < 0.5 * gArena && abs(hp.z) < 0.5 * gArena) ? 1.0 : 0.2;
        col = cB * gl * 0.22 * fog * inside;
        vec2 dh = hp.xz - gHeadPos;
        col += cA * exp(-dot(dh, dh) * 0.35) * 0.12 * (1.0 - step(0.001, gCrash));
    } else {
        col = vec3(0.004, 0.004, 0.008);
        col += cB * exp(-abs(rd.y) * 8.0) * (0.03 + low * 0.12);
        vec2 sp = vec2(atan(rd.z, rd.x), asin(clamp(rd.y, -1.0, 1.0))) * 60.0;
        vec2 sid = floor(sp);
        float sh = hash21(sid);
        if (sh > 0.93 && rd.y > 0.0) {
            vec2 off = (vec2(hash21(sid + 3.1), hash21(sid + 7.7)) - 0.5) * 0.6;
            float d = length(fract(sp) - 0.5 - off);
            float tw = 0.5 + 0.5 * sin(uClock * (1.5 + sh * 3.0) + sh * 40.0);
            col += mix(cA, vec3(1.0), 0.6) * (1.0 - smoothstep(0.0, 0.15, d)) * tw
                * (0.2 + high * 1.2) * smoothstep(0.0, 0.1, rd.y);
        }
    }

    // Arena walls: translucent fields with a bright top edge, in front of whatever was hit.
    vec2 span = arenaSpan(ro, rd);
    for (int w = 0; w < 2; w++) {
        float tw = w == 0 ? span.x : span.y;
        if (span.x < span.y && tw > 0.0 && tw < tHit) {
            vec3 wp = ro + rd * tw;
            if (wp.y >= 0.0 && wp.y <= gWall) {
                float wpix = tw / (720.0 * FOCAL);
                float wfog = exp(-tw * 0.03);
                float top = 1.0 - smoothstep(wpix, wpix * 2.5 + 0.01, gWall - wp.y);
                float along = abs(wp.x) > abs(wp.z) ? wp.z : wp.x;
                float vl = 1.0 - smoothstep(wpix, wpix * 2.0, abs(fract(along / 4.0 + 0.5) - 0.5) * 4.0);
                col += cB * (0.03 + top * 0.9 + vl * 0.1) * wfog * (0.5 + 0.5 * wp.y / gWall);
            }
        }
    }

    // The cycle: a white-hot light at the head of the trail.
    if (gCrash <= 0.0) {
        float depth;
        vec2 hs = project(vec3(gHeadPos.x, 0.45, gHeadPos.y), ro, fw, rt, up, depth);
        if (depth > 0.1) {
            float r = 0.10 * FOCAL / depth;
            float d = length(sc - hs);
            col += vec3(1.0, 0.97, 0.92) * exp(-pow(d / r, 2.0)) * (0.8 + punch);
            col += cA * exp(-d / (r * 2.5)) * 0.18 * (1.0 + punch);
        }
    }

    // Crash: flash, fireball, sparks.
    if (gCrash > 0.0) {
        float tau = gCrash * gCrashSeconds;
        float fade = pow(1.0 - gCrash, 1.5);
        vec3 c = vec3(gCrashPos.x, 0.5, gCrashPos.y);
        float depth;
        vec2 cs = project(c, ro, fw, rt, up, depth);
        if (depth > 0.1) {
            float radius = (0.6 + 4.0 * (1.0 - exp(-tau * 2.0))) * FOCAL / depth;
            float d = length(sc - cs);
            col += mix(vec3(1.0, 0.95, 0.85), cA, 0.4) * exp(-pow(d / radius, 2.0))
                * pow(1.0 - gCrash, 3.0) * 1.5;
        }
        for (int i = 0; i < SPARKS; i++) {
            float fi = float(i);
            float h1 = hash21(vec2(fi, 1.7));
            float h2 = hash21(vec2(fi, 5.3));
            float h3 = hash21(vec2(fi, 9.1));
            float h4 = hash21(vec2(fi, 13.9));
            vec3 dir = normalize(vec3(h1 - 0.5, 0.35 + h2 * 0.8, h3 - 0.5));
            float speed = 3.0 + h4 * 8.0;
            vec3 p = c + dir * speed * (1.0 - exp(-tau * 1.6)) / 1.6;
            p.y = max(p.y - 1.2 * tau * tau, 0.02);
            vec2 ps = project(p, ro, fw, rt, up, depth);
            if (depth > 0.1) {
                float r = 0.06 * FOCAL / depth;
                float d = length(sc - ps);
                col += mix(vec3(1.0, 0.95, 0.85), cA, h2)
                    * (exp(-pow(d / r, 2.0)) + 0.25 * exp(-d / (r * 4.0))) * fade;
            }
        }
        col += vec3(1.0, 0.9, 0.8) * exp(-tau * 7.0) * 0.9;
    }

    if (!ready) {
        col = vec3(0.0);
    }
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


def make_script_op(rack, kind, name, text, x, y):
    """Script CHOP or TOP with its callbacks replaced by text."""
    node = place(rack.create(kind, name), x, y)
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


def make_cycle_top(rack, name, which, width, height, x, y):
    node = make_script_op(rack, scriptTOP, name,
                          CYCLE_TOP_CALLBACKS.replace('__WHICH__', which), x, y)
    if hasattr(node.par, 'format'):
        choose(node.par.format, 'rgba32float')
    set_top_res(node, width, height)
    if hasattr(node.par, 'resmult'):
        node.par.resmult = False
    return node


def install_visual(rack):
    """Replace the picture with the light cycle arena.

    Leaves the player, the track menu, and audio_out alone. The picture reads
    the raw band levels through vis_features and the spectrum through spec_shape;
    cycle_sim drives the cycle and the two cycle TOPs hand its state to the shader.
    """
    if rack is None:
        print('music_rack: /project1/music_rack is missing.')
        return None

    for name in (
        'preview', 'picture', 'level', 'brightness', 'color', 'motion', 'circle', 'bg',
        'visual', 'visual_shader', 'levels_samples', 'levels_image',
        'spec_mag', 'spec_order', 'spec_bins', 'spec_lag', 'spec_gain', 'spec_limit', 'spec_image',
        'vis_features', 'vis_features_callbacks', 'spec_shape', 'spec_shape_callbacks',
        'cycle_sim', 'cycle_arena', 'cycle_arena_callbacks', 'cycle_hist', 'cycle_hist_callbacks',
    ):
        destroy_named(rack, name)

    spectrum = rack.op('spectrum')
    missing = [name for name in FEATURE_SOURCES + ('spectrum',) if rack.op(name) is None]
    if missing:
        print('music_rack: %s missing. Run the full build first.' % missing)
        return None

    ensure_visual_controls(rack)

    features = make_script_op(rack, scriptCHOP, 'vis_features', FEATURE_CALLBACKS, 420, 80)

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
    shaper = make_script_op(
        rack, scriptCHOP, 'spec_shape',
        SPEC_CALLBACKS.replace('__LOG_INPUT__', 'True' if log_input else 'False'),
        1260, -80)
    wire(shaper, bins)

    sim = place(rack.create(textDAT, 'cycle_sim'), 980, -520)
    sim.text = CYCLE_SIM
    arena = make_cycle_top(rack, 'cycle_arena', 'arena', 640, 640, 1260, -300)
    hist = make_cycle_top(rack, 'cycle_hist', 'hist', 64, 2049, 1260, -480)

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
        ('uPunch', 'parent().par.Punch'),
        ('uClock', 'absTime.seconds'),
    ])
    wire(visual, levels_image, 0)
    wire(visual, arena, 1)
    wire(visual, hist, 2)
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
    for node in (features, shaper, arena, hist, visual, preview):
        report(node)
    try:
        features.cook(force=True)
        shaper.cook(force=True)
        arena.cook(force=True)
        hist.cook(force=True)
        print('music_rack: features %s' % [c.name for c in features.chans()])
        print('music_rack: spectrum source %s samples -> %s bands' % (bins.numSamples, shaper.numSamples))
        print('music_rack: arena %sx%s, history %sx%s' % (
            arena.width, arena.height, hist.width, hist.height))
    except Exception as err:
        print('music_rack: analysis check failed:', err)

    try:
        preview.selected = True
        preview.openViewer()
    except Exception as err:
        print('music_rack: viewer did not open by itself (%s). Click preview and press v.' % err)

    print('')
    print('A window should be open on preview.')
    print('Light cycle arena: the cycle drags the spectrum behind it as a glowing ribbon,')
    print('turns on kicks, and races in loud sections. When it hits its own trail or a wall')
    print('it explodes, the camera pulls up over the arena, and a new run starts.')
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
    print('preview is a light cycle arena: the cycle drags the spectrum as a ribbon, turns on kicks, and crashes into its own trail.')
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
