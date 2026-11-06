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


def bind_time(visual):
    """Drive the cloud drift from a uniform. The GLSL TOP has no built-in clock."""
    seq = None
    try:
        seq = visual.seq.vec
    except Exception:
        seq = None
    if seq is not None:
        try:
            if int(seq.numBlocks) < 1:
                seq.numBlocks = 1
        except Exception as err:
            print('music_rack: time uniform slot:', err)
    if not hasattr(visual.par, 'vec0name') or not hasattr(visual.par, 'vec0valuex'):
        names = [p.name for p in visual.pars() if 'vec' in p.name.lower()]
        print('music_rack: could not bind a time uniform. Nearby: %s' % names[:30])
        return False
    visual.par.vec0name = 'uTime'
    visual.par.vec0valuex.expr = 'absTime.seconds'
    return True


def prepare_spectrum(rack, spectrum):
    """Return a CHOP whose samples are the frequency curve, loudest bins not crushed to 1."""
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

    try:
        source.cook(force=True)
        count = int(source.numSamples)
        rate = float(source.rate or 0)
    except Exception as err:
        print('music_rack: spectrum measure:', err)
        count = 0
        rate = 0

    if count > 256 and rate > 0:
        spec_bins = place(rack.create(resampleCHOP, 'spec_bins'), 980, -80)
        if hasattr(spec_bins.par, 'method'):
            choose(spec_bins.par.method, 'average', 'max')
        if hasattr(spec_bins.par, 'timeslice'):
            spec_bins.par.timeslice = True
        wire(spec_bins, source)
        if hasattr(spec_bins.par, 'rate'):
            spec_bins.par.rate = 160.0 * rate / float(count)
        try:
            spec_bins.cook(force=True)
        except Exception as err:
            print('music_rack: spectrum resample:', err)
        source = spec_bins

    lagged = place(rack.create(lagCHOP, 'spec_lag'), 1260, -80)
    if hasattr(lagged.par, 'lagmethod'):
        choose(lagged.par.lagmethod, 'value', 'amp')
    if hasattr(lagged.par, 'lag1'):
        lagged.par.lag1 = 0.16
    if hasattr(lagged.par, 'lag2'):
        lagged.par.lag2 = 0.40
    if hasattr(lagged.par, 'lagunit'):
        choose(lagged.par.lagunit, 'seconds')
    if hasattr(lagged.par, 'timeslice'):
        lagged.par.timeslice = True
    wire(lagged, source)
    return lagged


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


def add_controls(rack):
    page = rack.appendCustomPage('Music')

    track = as_par(page.appendMenu('Track', label='Track'))

    play = as_par(page.appendToggle('Play', label='Play'))
    play.default = False
    play.val = False

    def add_float(name, label, default, lo, hi):
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

    add_float('Volume', 'Volume', 0.25, 0, 1)
    add_float('Lowgain', 'Low Gain', 4, 0, 20)
    add_float('Midgain', 'Mid Gain', 5, 0, 20)
    add_float('Highgain', 'High Gain', 6, 0, 20)
    add_float('Rmsgain', 'RMS Gain', 3, 0, 20)
    add_float('Kickthresh', 'Kick Threshold', 0.3, 0, 1)

    as_par(page.appendPulse('Reloadtracks', label='Reload Tracks'))

    folder = as_par(page.appendStr('Musicfolder', label='Music Folder'))
    folder.default = MUSIC_DIR
    folder.val = MUSIC_DIR
    return track


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
        'spectrum is the frequency curve. The preview cloud reads it.',
        'preview is the picture: a colored particle cloud driven by the track.',
        '',
        'New files: drop them in the music folder, then pulse Reload Tracks.',
        'Visuals you build later should read only audio_out (and spectrum if they need the curve).',
        'Running the build script again replaces this whole component.',
    ])
    return note


VISUAL_SHADER = r'''
layout(location = 0) out vec4 fragColor;
uniform float uTime;

float levelAt(int i)
{
    ivec2 s = textureSize(sTD2DInputs[0], 0);
    if (s.x < 1 || s.y < 1) {
        return 0.0;
    }
    if (s.x >= 5) {
        return texelFetch(sTD2DInputs[0], ivec2(clamp(i, 0, s.x - 1), 0), 0).r;
    }
    if (s.y >= 5) {
        return texelFetch(sTD2DInputs[0], ivec2(0, clamp(i, 0, s.y - 1)), 0).r;
    }
    return 0.0;
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

vec2 spectrumRange()
{
    ivec2 s = textureSize(sTD2DInputs[1], 0);
    int n = max(s.x, s.y);
    int horizontal = s.x >= s.y ? 1 : 0;
    float lo = 1e9;
    float hi = -1e9;
    for (int k = 0; k < 32; k++) {
        int i = (k * max(n - 1, 0)) / 31;
        ivec2 coord = (horizontal == 1)
            ? ivec2(clamp(i, 0, max(s.x - 1, 0)), 0)
            : ivec2(0, clamp(i, 0, max(s.y - 1, 0)));
        float v = texelFetch(sTD2DInputs[1], coord, 0).r;
        lo = min(lo, v);
        hi = max(hi, v);
    }
    if (hi < lo + 0.0008) {
        hi = lo + 0.0008;
    }
    return vec2(lo, hi);
}

float shaped(float u, vec2 rng)
{
    ivec2 s = textureSize(sTD2DInputs[1], 0);
    float lu = pow(clamp(u, 0.0, 1.0), 1.45);
    float v = 0.0;
    if (s.x >= s.y && s.x > 1) {
        int x = clamp(int(lu * float(s.x - 1) + 0.5), 0, s.x - 1);
        v = texelFetch(sTD2DInputs[1], ivec2(x, 0), 0).r;
    } else if (s.y > 1) {
        int y = clamp(int(lu * float(s.y - 1) + 0.5), 0, s.y - 1);
        v = texelFetch(sTD2DInputs[1], ivec2(0, y), 0).r;
    }
    return clamp((v - rng.x) / max(rng.y - rng.x, 0.0008), 0.0, 1.0);
}

vec3 sparkLayer(vec2 uv, float t, vec2 grid, float speed, float spread, vec2 rng)
{
    vec2 p = uv * grid + vec2(t * speed, t * speed * 0.41);
    vec2 id = floor(p);
    vec2 gv = fract(p) - 0.5;
    float n = hash21(id);
    float n2 = hash21(id + 19.1);
    vec2 wobble = 0.08 * vec2(
        sin(t * (0.8 + n) + n * 6.28318),
        cos(t * (0.55 + n2) + n2 * 6.28318));
    vec2 d = gv - (vec2(n, n2) - 0.5) * 0.75 - wobble;
    float band = shaped(fract((id.x + 0.5) / grid.x), rng);
    float rad = mix(0.045, 0.24, n2) * (0.85 + band * 0.15) * spread;
    float glow = exp(-dot(d, d) / max(rad * rad, 0.0004));
    float core = exp(-dot(d, d) / max(rad * rad * 0.1, 0.00005));
    float keep = smoothstep(0.12, 0.5, n);
    vec3 tint = palette(n * 0.85 + band * 0.08 + id.y * 0.03 + t * 0.025);
    float amp = keep * (0.42 + band * 0.28) * (0.75 + 0.25 * sin(t * 1.6 + n * 20.0));
    return tint * glow * amp + vec3(1.0, 0.96, 0.92) * core * amp * 0.4;
}

void main()
{
    vec2 rng = spectrumRange();
    float t = uTime;
    vec2 uv = vUV.st;
    float low = clamp(levelAt(0), 0.0, 1.0);
    float mid = clamp(levelAt(1), 0.0, 1.0);
    float high = clamp(levelAt(2), 0.0, 1.0);
    float rms = clamp(levelAt(3), 0.0, 1.0);
    float kick = clamp(levelAt(4), 0.0, 1.0);

    vec2 p = (uv - 0.5) * vec2(1.7778, 1.0);
    p *= 1.45 * (1.0 - low * 0.06);
    float here = shaped(clamp(uv.x, 0.0, 1.0), rng);
    p += vec2(
        sin(p.y * 2.2 + t * 0.65) * 0.08,
        -0.217 + sin(p.x * 1.6 - t * 0.4) * 0.06);

    vec2 q = vec2(
        fbm(p + vec2(0.0, t * 0.08)),
        fbm(p + vec2(5.2, 1.3) - t * 0.055));
    vec2 r = vec2(
        fbm(p + 3.5 * q + vec2(1.7, 9.2) + t * 0.07),
        fbm(p + 3.5 * q + vec2(8.3, 2.8) - t * 0.05));
    float f = fbm(p * (1.1 + mid * 0.05) + 3.7 * r);

    vec3 deep = vec3(0.045, 0.02, 0.09);
    vec3 cA = palette(f * 0.9 + q.x * 0.5 + high * 0.10 + here * 0.08 + t * 0.02);
    vec3 cB = palette(0.42 + r.y * 0.55 + length(q) * 0.3 + low * 0.08);
    float body = smoothstep(0.15, 0.9, f);
    float ridge = pow(smoothstep(0.32, 0.95, f), 1.45);

    vec3 col = mix(deep, cA, 0.42 + body * 0.7);
    col += cB * ridge * (0.7 + rms * 0.32 + low * 0.16);
    col += cA.bgr * pow(clamp(length(q), 0.0, 1.0), 1.35) * (0.22 + high * 0.16);
    col += palette(uv.x * 0.15 + here * 0.10 + t * 0.03) * here * (0.05 + rms * 0.08);

    float rad = length(p);
    float core = exp(-rad * rad * (1.45 - low * 0.2));
    col += palette(0.58 + high * 0.12 + t * 0.03) * core * (0.55 + low * 0.4 + kick * 0.3);

    vec2 suv = uv + vec2(0.03 * sin(t * 0.2), low * 0.02);
    col += sparkLayer(suv, t, vec2(7.0, 4.0), 0.04, 1.55, rng);
    col += sparkLayer(suv + vec2(19.2, 3.7), t, vec2(15.0, 8.5), -0.055, 1.05, rng);
    col += sparkLayer(suv + vec2(4.4, 11.0), t, vec2(32.0, 18.0), 0.085, 0.72, rng);

    col += palette(0.08 + high * 0.1 + t * 0.04) * kick * exp(-rad * rad * 1.6) * 0.28;

    float luma = dot(col, vec3(0.299, 0.587, 0.114));
    col = mix(vec3(luma), col, 1.28);
    col = 1.0 - exp(-col * 1.15);
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


def install_visual(rack):
    """Replace the picture with a colored particle cloud.

    Leaves the player, the track menu, and audio_out alone.
    """
    if rack is None:
        print('music_rack: /project1/music_rack is missing.')
        return None

    for name in (
        'preview', 'picture', 'level', 'brightness', 'color', 'motion', 'circle', 'bg',
        'visual', 'visual_shader', 'levels_samples', 'levels_image',
        'spec_mag', 'spec_order', 'spec_bins', 'spec_lag', 'spec_gain', 'spec_limit', 'spec_image',
    ):
        destroy_named(rack, name)

    audio = rack.op('audio_out')
    spectrum = rack.op('spectrum')
    if audio is None or spectrum is None:
        print('music_rack: audio_out or spectrum is missing. Run the full build first.')
        return None

    levels = place(rack.create(shuffleCHOP, 'levels_samples'), 700, 80)
    if hasattr(levels.par, 'method'):
        choose(levels.par.method, 'swap')
    if hasattr(levels.par, 'timeslice'):
        levels.par.timeslice = True
    wire(levels, audio)

    levels_image = place(rack.create(choptoTOP, 'levels_image'), 980, 80)
    if hasattr(levels_image.par, 'dataformat'):
        choose(levels_image.par.dataformat, 'r', 'red')
    if hasattr(levels_image.par, 'layout'):
        choose(levels_image.par.layout, 'rowscropped')
    if hasattr(levels_image.par, 'clamp'):
        levels_image.par.clamp = True
    feed_chop(levels_image, levels)
    size_data_image(levels_image, levels)

    bins = prepare_spectrum(rack, spectrum)
    spec_image = place(rack.create(choptoTOP, 'spec_image'), 1820, -80)
    if hasattr(spec_image.par, 'dataformat'):
        choose(spec_image.par.dataformat, 'r', 'red')
    if hasattr(spec_image.par, 'layout'):
        choose(spec_image.par.layout, 'rowscropped')
    if hasattr(spec_image.par, 'clamp'):
        spec_image.par.clamp = False
    feed_chop(spec_image, bins)
    size_data_image(spec_image, bins)

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
    bind_time(visual)
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
    report(visual)
    report(preview)
    try:
        levels.cook(force=True)
        bins.cook(force=True)
        levels_image.cook(force=True)
        spec_image.cook(force=True)
        print('music_rack: level samples %s, spectrum bins %s' % (levels.numSamples, bins.numSamples))
        print('music_rack: level image %sx%s, spectrum image %sx%s' % (
            levels_image.width, levels_image.height, spec_image.width, spec_image.height))
        if bins.numChans > 0 and bins.numSamples > 0:
            ch = bins.chans()[0]
            n = int(bins.numSamples)
            idxs = [0, n // 4, n // 2, (3 * n) // 4, n - 1]
            vals = [round(float(ch[i]), 4) for i in idxs if 0 <= i < n]
            print('music_rack: spectrum curve %s' % vals)
    except Exception as err:
        print('music_rack: analysis count failed:', err)

    try:
        preview.selected = True
        preview.openViewer()
    except Exception as err:
        print('music_rack: viewer did not open by itself (%s). Click preview and press v.' % err)

    print('')
    print('A window should be open on preview.')
    print('Colored clouds and particles fill the frame and keep drifting.')
    print('The track brightens the cloud and shifts its color. It should not jump or flicker.')
    print('Leave Play on. If the window is behind TouchDesigner, click preview and press v.')
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
    print('preview is a colored particle cloud. Bass swells it, highs shift the color, kicks flash through it.')
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
