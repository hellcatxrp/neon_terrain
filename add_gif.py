# Draw the KOTH gif in the dark space under the crown, and drop REST_LIFT
# from 0.30 to 0.20 so the resting line sits just above the art.
#
# preview stays on visual. A regular GLSL TOP has three inputs, and visual
# already uses all three, so the keyed gif and the title card share input 2:
# bottom half is the placed gif, top half is title_card.
#
# Textport:
#   exec(open(r'C:\Users\James\Desktop\TOUCH\add_gif.py', encoding='utf-8').read())
#
# Undo the crown and the gif (Play, the track, and Source stay):
#   exec(open(r'C:\Users\James\Desktop\TOUCH\restore_picture.py', encoding='utf-8').read())
#
# 2026-11-10: sharper crown. crown_key renders at visual's resolution and
#   crown_stack copies it and title_card texel for texel (no 50/50 split sized
#   by the title card, which squeezed the gif into 161x272). The original olive
#   key is back as Key "classic"; "auto" measures the backdrop and de-fringes.
#   Asset and Asset Key menus plus a Reload Assets pulse on the Music page pick
#   the file in assets\. Gif Scale is the asset's longer side in 720p pixels.
# 2026-11-10: Gif Scale, Gif X, Gif Y also on the Music page, bound both ways
#   to the crown_vis sliders.
# 2026-11-10: after a rerun renames gif_* to crown_*, point Pixel Shader at the
#   renamed DATs again. The stale name was the red X, the olive picture, the
#   huge crown, and the white rectangle.

import re

ASSET_DIR = r'C:\Users\James\Desktop\TOUCH\assets'
GIF = ASSET_DIR + r'\koth_crown.gif'
RACK = '/project1/music_rack'
REST_LIFT = 0.20
# Uniforms on visual that describe crown_stack. restore_picture.py clears uGif*.
LAYOUT_UNIFORMS = ('uGifKeyW', 'uGifKeyH', 'uGifCardW', 'uGifCardH')

REST_RE = re.compile(r'const float REST_LIFT = [0-9.]+\s*;')
TITLE_OLD = '''// Glyph coverage. Coordinates outside the card contribute nothing.
float titleGlyph(vec2 texUV)
{
    float inside = step(0.0, texUV.x) * step(texUV.x, 1.0) * step(0.0, texUV.y) * step(texUV.y, 1.0);
    return texture(sTD2DInputs[2], clamp(texUV, 0.0, 1.0)).a * inside;
}
'''
TITLE_NEW = '''// Glyph coverage. Coordinates outside the card contribute nothing.
// GIF_TITLE begin
// crown_stack layout, set by add_gif.py: crown_key fills the bottom rows and
// title_card sits above it at the left. Both are copied texel for texel.
// With these four at 0 the older half-and-half stack is read instead.
uniform float uGifKeyW;
uniform float uGifKeyH;
uniform float uGifCardW;
uniform float uGifCardH;

bool gifStacked()
{
    return uGifKeyW >= 1.0 && uGifKeyH >= 1.0 && uGifCardW >= 1.0 && uGifCardH >= 1.0;
}

// title_card's own size, so the title keeps its aspect.
ivec2 gifCardSize(ivec2 stackSize)
{
    if (gifStacked()) {
        return ivec2(int(uGifCardW + 0.5), int(uGifCardH + 0.5));
    }
    return ivec2(stackSize.x, stackSize.y / 2);
}

float titleGlyph(vec2 texUV)
{
    float inside = step(0.0, texUV.x) * step(texUV.x, 1.0) * step(0.0, texUV.y) * step(texUV.y, 1.0);
    vec2 stackSize = vec2(textureSize(sTD2DInputs[2], 0));
    vec2 stacked;
    if (gifStacked()) {
        // The same texels as sampling title_card itself, clamped to its edge.
        vec2 card = vec2(uGifCardW, uGifCardH);
        vec2 px = clamp(texUV * card, vec2(0.5), card - 0.5);
        stacked = (px + vec2(0.0, uGifKeyH)) / stackSize;
    } else {
        stacked = vec2(texUV.x, 0.5 + texUV.y * 0.5);
        float seam = 0.5 / max(stackSize.y, 1.0);
        stacked.y = max(stacked.y, 0.5 + seam);
        stacked = clamp(stacked, 0.0, 1.0);
    }
    return texture(sTD2DInputs[2], stacked).a * inside;
}
// GIF_TITLE end
'''
SIZE_OLD = '    ivec2 size = textureSize(sTD2DInputs[2], 0);\n'
SIZE_MARK = 'size = gifCardSize(size);'
SIZE_LINE = '    size = gifCardSize(size); // title_card inside crown_stack\n'
SIZE_NEW = SIZE_OLD + SIZE_LINE
# Written by the half-and-half version. Replaced by SIZE_LINE on the next run.
SIZE_LEGACY = '    size.y /= 2; // top half of crown_stack is the title card\n'
GRAIN = '    col += grain * 0.018;\n'
GIF_BEGIN = '// GIF_UNDER begin'
GIF_END = '// GIF_UNDER end'
GIF_BLOCK = '''    col += grain * 0.018;
    // GIF_UNDER begin
    // Keyed crown from the bottom rows of input 2. It shows only in dark pixels.
    {
        ivec2 stackSize = textureSize(sTD2DInputs[2], 0);
        vec4 gifPix;
        if (gifStacked()) {
            // crown_key matches this frame: fetch the one texel under this pixel, 1:1.
            vec2 keySize = vec2(uGifKeyW, uGifKeyH);
            ivec2 px = ivec2(clamp(floor(vUV.st * keySize), vec2(0.0), keySize - 1.0));
            gifPix = texelFetch(sTD2DInputs[2], px, 0);
        } else {
            vec2 gifUV = vec2(vUV.x, vUV.y * 0.5);
            float gifSeam = 0.5 / max(float(stackSize.y), 1.0);
            gifUV.y = min(gifUV.y, 0.5 - gifSeam);
            gifPix = texture(sTD2DInputs[2], gifUV);
        }
        float gifLuma = max(col.r, max(col.g, col.b));
        float gifUnder = 1.0 - smoothstep(0.05, 0.18, gifLuma);
        col = mix(col, gifPix.rgb, clamp(gifPix.a * gifUnder, 0.0, 1.0));
    }
    // GIF_UNDER end
'''

KEY_SHADER = r'''layout(location = 0) out vec4 fragColor;
uniform float uGifScale;  // longer side of the asset, in pixels of a 1280x720 frame
uniform float uGifX;      // centre of the asset, 0..1 across the frame
uniform float uGifY;      // bottom edge of the asset, 0..1 up the frame
uniform float uKeyMode;   // 0 classic olive, 1 auto (measured backdrop), 2 none (asset alpha)

// Gif Scale is counted in a 1280x720 frame whatever this TOP's size is.
// This TOP matches visual, and crown_stack and visual copy it 1:1.
const vec2 FRAME = vec2(1280.0, 720.0);
// Auto key: colour distance from the measured backdrop where alpha ramps 0 to 1.
const float KEY_LO = 0.08;
const float KEY_HI = 0.16;

vec3 gBg = vec3(0.0);
int gMode = 0;

// Four texels just inside the corners: the backdrop as the Movie File In
// actually delivers it, rather than the value written in the file.
vec3 measuredBackdrop(ivec2 size)
{
    ivec2 m = min(ivec2(2), max(size - 1, ivec2(0)));
    ivec2 far = max(size - 1 - m, ivec2(0));
    vec3 c = texelFetch(sTD2DInputs[0], ivec2(m.x, m.y), 0).rgb
        + texelFetch(sTD2DInputs[0], ivec2(far.x, m.y), 0).rgb
        + texelFetch(sTD2DInputs[0], ivec2(m.x, far.y), 0).rgb
        + texelFetch(sTD2DInputs[0], ivec2(far.x, far.y), 0).rgb;
    return c * 0.25;
}

// One source texel, keyed, premultiplied.
vec4 keyedTexel(ivec2 t)
{
    vec4 c = texelFetch(sTD2DInputs[0], t, 0);
    if (gMode == 2) {
        return c;   // the asset's own alpha. Movie File In hands it over premultiplied.
    }
    vec3 diff = c.rgb - gBg;
    float a = smoothstep(KEY_LO, KEY_HI, length(diff));
    // Smallest coverage that keeps the unmixed colour inside 0..1. Part-covered
    // edge texels lose the backdrop instead of keeping an olive rim.
    vec3 up = max(diff, 0.0) / max(1.0 - gBg, vec3(1e-3));
    vec3 dn = max(-diff, 0.0) / max(gBg, vec3(0.12));
    float cover = max(max(max(up.r, up.g), max(up.b, max(dn.r, max(dn.g, dn.b)))), a);
    vec3 fg = clamp(gBg + diff / max(cover, 0.04), 0.0, 1.0);
    return vec4(fg * a, a);
}

// Sharp bilinear: each texel is a flat square, blended only across the last
// output pixel at its edge. Crisp at any Gif Scale, without stair steps.
vec4 sharpSample(vec2 uv, vec2 src, vec2 pxPerTexel)
{
    vec2 x = uv * src - 0.5;
    vec2 i = floor(x);
    vec2 f = x - i;
    vec2 k = max(pxPerTexel, vec2(1.0));
    f = clamp((f - 0.5) * k + 0.5, 0.0, 1.0);
    ivec2 hi = ivec2(src) - 1;
    ivec2 i0 = clamp(ivec2(i), ivec2(0), hi);
    ivec2 i1 = clamp(ivec2(i) + 1, ivec2(0), hi);
    vec4 a = keyedTexel(i0);
    vec4 b = keyedTexel(ivec2(i1.x, i0.y));
    vec4 c = keyedTexel(ivec2(i0.x, i1.y));
    vec4 d = keyedTexel(i1);
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

// The original key, unchanged: fixed olive, luma and chroma gates, one linear sample.
vec4 classicKey(vec2 local, float inside)
{
    vec4 s = texture(sTD2DInputs[0], clamp(local, 0.0, 1.0));
    vec3 olive = vec3(39.0, 40.0, 2.0) / 255.0;
    float d = distance(s.rgb, olive);
    float luma = max(s.r, max(s.g, s.b));
    float chroma = luma - min(s.r, min(s.g, s.b));
    float near = smoothstep(0.10, 0.18, d) * smoothstep(0.10, 0.22, luma);
    float vivid = smoothstep(0.22, 0.42, luma) * smoothstep(0.18, 0.36, chroma);
    float a = max(near, vivid) * inside;
    return vec4(s.rgb, a);
}

// Place the asset in the frame at its real aspect and key it. Straight alpha out.
void main()
{
    ivec2 srcI = max(textureSize(sTD2DInputs[0], 0), ivec2(1));
    vec2 src = vec2(srcI);
    float side = uGifScale / max(src.x, src.y);
    vec2 sizeUV = src * side / FRAME;
    vec2 origin = vec2(uGifX - sizeUV.x * 0.5, uGifY);
    vec2 local = (vUV.st - origin) / max(sizeUV, vec2(1e-4));
    float inside = step(0.0, local.x) * step(local.x, 1.0)
        * step(0.0, local.y) * step(local.y, 1.0);
    gMode = int(uKeyMode + 0.5);
    if (gMode <= 0) {
        fragColor = TDOutputSwizzle(classicKey(local, inside));
        return;
    }
    if (inside < 0.5) {
        fragColor = TDOutputSwizzle(vec4(0.0));
        return;
    }
    gBg = measuredBackdrop(srcI);
    // Output pixels per source texel. Below 1 the asset is shrunk, so average
    // up to 4x4 samples per pixel instead of skipping texels.
    vec2 outRes = uTDOutputInfo.res.zw;
    vec2 pxPerTexel = sizeUV * outRes / src;
    ivec2 n = ivec2(clamp(ceil(1.0 / max(pxPerTexel, vec2(1e-3))), vec2(1.0), vec2(4.0)));
    vec2 pixel = 1.0 / max(sizeUV * outRes, vec2(1e-3));
    vec4 acc = vec4(0.0);
    for (int j = 0; j < n.y; j++) {
        for (int i = 0; i < n.x; i++) {
            vec2 off = (vec2(float(i), float(j)) + 0.5) / vec2(n) - 0.5;
            acc += sharpSample(clamp(local + off * pixel, 0.0, 1.0), src, pxPerTexel);
        }
    }
    acc /= float(n.x * n.y);
    vec3 rgb = acc.a > 1e-4 ? acc.rgb / acc.a : vec3(0.0);
    fragColor = TDOutputSwizzle(vec4(clamp(rgb, 0.0, 1.0), clamp(acc.a, 0.0, 1.0)));
}
'''

STACK_SHADER = r'''layout(location = 0) out vec4 fragColor;

// Input 0 is crown_key, input 1 is title_card. Both are copied texel for texel:
// crown_key fills the bottom rows, title_card sits above it at the left.
// Nothing is scaled, so neither picture is resampled here.
void main()
{
    ivec2 p = ivec2(gl_FragCoord.xy);
    ivec2 keySize = textureSize(sTD2DInputs[0], 0);
    ivec2 cardSize = textureSize(sTD2DInputs[1], 0);
    vec4 c = vec4(0.0);
    if (p.y < keySize.y) {
        if (p.x < keySize.x) {
            c = texelFetch(sTD2DInputs[0], p, 0);
        }
    } else {
        ivec2 q = ivec2(p.x, p.y - keySize.y);
        if (q.x < cardSize.x && q.y < cardSize.y) {
            c = texelFetch(sTD2DInputs[1], q, 0);
        }
    }
    fragColor = TDOutputSwizzle(c);
}
'''

KEY_MODES = ('classic', 'auto', 'none')
KEY_LABELS = ('Olive (classic)', 'Olive (auto, de-fringed)', 'None (asset alpha)')
ASSET_PARS = ('Asset', 'Assetkey', 'Reloadassets')

# Parameter Execute DAT text for crown_vis/asset_callbacks. add_gif.py also
# runs it in its own namespace to share the folder and key functions.
ASSET_CALLBACKS = r'''# Written by add_gif.py. Watches Asset, Asset Key, Reload Assets, and
# Reload Tracks on music_rack. Repoints crown_movie without rebuilding.
import os

ASSET_DIR = r'C:\Users\James\Desktop\TOUCH\assets'
ASSET_EXT = ('.gif', '.png', '.jpg', '.jpeg', '.mp4', '.mov')
DEFAULT_ASSET = 'koth_crown.gif'
KEY_MODES = ('classic', 'auto', 'none')
_busy = {'on': False}


def asset_rows(folder=None):
    folder = folder or ASSET_DIR
    rows = []
    try:
        names = os.listdir(folder)
    except OSError as err:
        print('assets: cannot read %s: %s' % (folder, err))
        return rows
    for name in names:
        full = os.path.join(folder, name)
        if os.path.isfile(full) and os.path.splitext(name)[1].lower() in ASSET_EXT:
            rows.append((name, full))
    rows.sort(key=lambda pair: pair[0].casefold())
    return rows


def default_key(name):
    # A PNG usually carries its own alpha. Everything else is taken to sit on olive.
    return 'none' if name.lower().endswith('.png') else 'classic'


def _table(base):
    return base.op('asset_table') if base is not None else None


def stored_keys(base):
    keys = {}
    table = _table(base)
    if table is None:
        return keys
    for r in range(table.numRows):
        if table.numCols > 2 and str(table[r, 2].val) in KEY_MODES:
            keys[str(table[r, 0].val)] = str(table[r, 2].val)
    return keys


def asset_name(rack):
    return str(rack.par.Asset.eval() or '') if hasattr(rack.par, 'Asset') else ''


def asset_path(rack, base):
    name = asset_name(rack)
    if not name:
        return ''
    full = os.path.join(ASSET_DIR, name)
    return full if os.path.isfile(full) else ''


def refresh_assets(rack, base):
    """Rebuild the Asset menu from the folder. Keeps the pick and each asset's key."""
    if not hasattr(rack.par, 'Asset'):
        return []
    rows = asset_rows()
    keys = stored_keys(base)
    table = _table(base)
    if table is not None:
        table.clear()
        for name, full in rows:
            table.appendRow([name, full.replace('\\', '/'), keys.get(name, default_key(name))])
    par = rack.par.Asset
    current = asset_name(rack)
    names = [name for name, _full in rows]
    if names:
        par.menuNames = names
        par.menuLabels = names
    else:
        par.menuNames = [current or DEFAULT_ASSET]
        par.menuLabels = ['(no assets in %s)' % ASSET_DIR]
    if names and current not in names:
        pick = DEFAULT_ASSET if DEFAULT_ASSET in names else names[0]
        _busy['on'] = True
        try:
            par.val = pick
        finally:
            _busy['on'] = False
        print('assets: %s is gone from the folder. Asset is now %s.' % (current or '(blank)', pick))
    return rows


def set_uniform(node, name, value):
    i = 0
    while node is not None and hasattr(node.par, 'vec%dname' % i) and i < 64:
        if str(getattr(node.par, 'vec%dname' % i) or '') == name:
            getattr(node.par, 'vec%dvaluex' % i).expr = repr(float(value))
            return True
        i += 1
    return False


def key_index(rack):
    value = str(rack.par.Assetkey.eval() or '') if hasattr(rack.par, 'Assetkey') else ''
    return KEY_MODES.index(value) if value in KEY_MODES else 0


def apply_key(rack, base, remember=True):
    index = key_index(rack)
    key = base.op('crown_key') if base is not None else None
    if key is not None and not set_uniform(key, 'uKeyMode', index):
        print('assets: crown_key has no uKeyMode uniform. Run add_gif.py again.')
    table = _table(base)
    if remember and table is not None:
        name = asset_name(rack)
        for r in range(table.numRows):
            if str(table[r, 0].val) == name and table.numCols > 2:
                table[r, 2] = KEY_MODES[index]
    return index


def apply_asset(rack, base, force=False):
    """Point crown_movie at the chosen file. Its remembered key comes with it."""
    path = asset_path(rack, base)
    if not path:
        print('assets: %s is not in %s.' % (asset_name(rack) or '(blank)', ASSET_DIR))
        return ''
    name = asset_name(rack)
    key = stored_keys(base).get(name, default_key(name))
    if hasattr(rack.par, 'Assetkey') and str(rack.par.Assetkey.eval()) != key:
        _busy['on'] = True
        try:
            rack.par.Assetkey = key
        finally:
            _busy['on'] = False
    apply_key(rack, base, remember=False)
    movie = base.op('crown_movie') if base is not None else None
    if movie is None:
        return path
    current = str(movie.par.file.eval() or '').replace('\\', '/').lower()
    if force or current != path.replace('\\', '/').lower():
        movie.par.file = path
        if hasattr(movie.par, 'reloadpulse'):
            movie.par.reloadpulse.pulse()
        print('assets: crown_movie plays %s, key %s.' % (path, key))
    return path


def onValueChange(par, prev):
    if _busy['on']:
        return
    if par.name == 'Asset':
        apply_asset(par.owner, me.parent())
    elif par.name == 'Assetkey':
        apply_key(par.owner, me.parent())
    return


def onValuesChanged(changes):
    for change in changes:
        onValueChange(change.par, getattr(change, 'prev', None))
    return


def onPulse(par):
    if par.name in ('Reloadassets', 'Reloadtracks'):
        refresh_assets(par.owner, me.parent())
        apply_asset(par.owner, me.parent())
    return


def onExpressionChange(par, prev):
    return


def onExportChange(par, prev):
    return
'''

OWNED = (
    'crown_over', 'crown_stack', 'crown_key', 'crown_movie',
    'crown_over_shader', 'crown_stack_shader', 'crown_key_shader',
)
# Kept across runs: the Select and Out TOPs, and the asset menu state.
KEPT = ('crown_title_in', 'crown_out', 'asset_callbacks', 'asset_table')
# Used only while a live crown_stack is still feeding visual.
TEMP_NAMES = (
    'gif_movie', 'gif_key', 'gif_stack', 'gif_key_shader', 'gif_stack_shader',
)
CROWN_NAMES = (
    'crown_movie', 'crown_key', 'crown_stack', 'crown_key_shader', 'crown_stack_shader',
)


def norm(text):
    return (text or '').replace('\r\n', '\n').replace('\r', '\n')


def replace_span(text, begin, end, block):
    b = text.find(begin)
    if b < 0:
        return None
    e = text.find(end, b + len(begin))
    if e < 0:
        return None
    e += len(end)
    if e < len(text) and text[e] == '\n':
        e += 1
    if not block.endswith('\n'):
        block += '\n'
    return text[:b] + block + text[e:]


def patch_gif(text):
    """Return (new text, notes). On a bad shader, return (None, reasons) and change nothing."""
    text = norm(text)
    reasons = []
    rest = REST_RE.findall(text)
    if len(rest) != 1:
        reasons.append('REST_LIFT declarations: %s' % len(rest))
    title_state = 'old' if text.count(TITLE_OLD) == 1 else ('new' if '// GIF_TITLE begin' in text else 'missing')
    if title_state == 'missing' or text.count(TITLE_OLD) > 1:
        reasons.append('titleGlyph is not the terrain function')
    if text.count(SIZE_OLD) != 1:
        reasons.append('title size line count: %s' % text.count(SIZE_OLD))
    if 'size.y /= 2;' in text and text.count(SIZE_LEGACY) != 1:
        reasons.append('title half-height count is wrong')
    if text.count(SIZE_MARK) > 1:
        reasons.append('title card size line count: %s' % text.count(SIZE_MARK))
    gif_marked = GIF_BEGIN in text
    if gif_marked and (text.count(GIF_BEGIN) != 1 or text.count(GIF_END) != 1):
        reasons.append('GIF_UNDER markers are uneven')
    if not gif_marked and text.count(GRAIN) != 1:
        reasons.append('grain line count: %s' % text.count(GRAIN))
    if 'sTD2DInputs[3]' in text:
        reasons.append('shader already samples a fourth input')
    if reasons:
        return None, reasons

    text = REST_RE.sub('const float REST_LIFT = %.2f;' % REST_LIFT, text, count=1)
    notes = ['REST_LIFT']
    title_span = TITLE_NEW[TITLE_NEW.find('// GIF_TITLE begin'):]
    if title_state == 'old':
        text = text.replace(TITLE_OLD, TITLE_NEW, 1)
        notes.append('title')
    else:
        updated = replace_span(text, '// GIF_TITLE begin', '// GIF_TITLE end', title_span)
        if updated is None:
            return None, ['GIF_TITLE markers could not be updated']
        text = updated
        notes.append('title kept')
    if SIZE_MARK in text:
        notes.append('title size kept')
    elif SIZE_LEGACY in text:
        text = text.replace(SIZE_LEGACY, SIZE_LINE, 1)
        notes.append('title size from half stack')
    else:
        text = text.replace(SIZE_OLD, SIZE_NEW, 1)
        notes.append('title size')
    if gif_marked:
        gif_span = GIF_BLOCK[GIF_BLOCK.find(GIF_BEGIN):]
        updated = replace_span(text, GIF_BEGIN, GIF_END, gif_span)
        if updated is None:
            return None, ['GIF_UNDER could not be updated']
        text = updated
        notes.append('gif kept')
    else:
        text = text.replace(GRAIN, GIF_BLOCK, 1)
        notes.append('gif')
    if REST_RE.findall(text) != ['const float REST_LIFT = %.2f;' % REST_LIFT]:
        return None, ['REST_LIFT did not land on %.2f' % REST_LIFT]
    if text.count(GIF_BEGIN) != 1 or text.count(SIZE_NEW) != 1 or 'size.y /= 2;' in text:
        return None, ['patch did not land once']
    if 'sTD2DInputs[3]' in text:
        return None, ['patch sampled a fourth input']
    return text, notes


def inside_td():
    try:
        op  # noqa: F821
    except NameError:
        return False
    return True


def choose(par, *options):
    available = list(par.menuNames) if hasattr(par, 'menuNames') else []
    for opt in options:
        if opt in available:
            par.val = opt
            return opt
    print('gif: could not set %s. Options: %s' % (par.name, available))
    return None


def place(node, x, y):
    node.nodeX = x
    node.nodeY = y
    return node


def set_top_res(node, width, height):
    if hasattr(node.par, 'outputresolution'):
        choose(node.par.outputresolution, 'custom')
    if hasattr(node.par, 'resolutionw'):
        node.par.resolutionw = width
    if hasattr(node.par, 'resolutionh'):
        node.par.resolutionh = height
    if hasattr(node.par, 'resmult'):
        node.par.resmult = False


def as_par(result):
    if isinstance(result, (list, tuple)):
        return result[0]
    return result


def input_owner(node, index=0):
    try:
        conn = list(node.inputConnectors)[index]
        links = list(conn.connections)
    except Exception:
        return None
    if len(links) != 1:
        return None
    return links[0].owner


def wire(dst, src, index=0):
    """Connect src's output to one input of dst, then check that input stayed put."""
    connectors = list(dst.inputConnectors)
    if index < 0 or index >= len(connectors):
        print('gif: %s has %s inputs, so input %s was not connected.' % (
            dst.path, len(connectors), index))
        return False
    inn = connectors[index]
    # Input.connect(operator) is how title_card is already wired to visual.
    # Leave the existing wire in place until a new one sticks. A text TOP has no operator.connect().
    try:
        inn.connect(src)
    except Exception as err:
        print('gif: wire %s -> %s input %s failed: %s' % (src.path, dst.path, index, err))
    owner = input_owner(dst, index)
    if owner is None or owner.path != src.path:
        try:
            outs = list(src.outputConnectors)
            if not outs:
                print('gif: %s has no output connector.' % src.path)
            else:
                outs[0].connect(inn)
        except Exception as err:
            print('gif: wire retry %s -> %s input %s failed: %s' % (
                src.path, dst.path, index, err))
        owner = input_owner(dst, index)
    if owner is None or owner.path != src.path:
        print('gif: %s input %s is %s, wanted %s.' % (
            dst.path, index, owner.path if owner else '(none)', src.path))
        return False
    return True


def op_path(value):
    if value is None:
        return ''
    if hasattr(value, 'path'):
        return value.path
    return str(value)


def bring_title(base, title):
    """A wire stops at the crown_vis boundary. A Select TOP reads title_card by path."""
    inlet = base.op('crown_title_in')
    if inlet is not None and not hasattr(inlet.par, 'top'):
        try:
            inlet.destroy()
        except Exception as err:
            print('gif: could not replace %s: %s' % (inlet.path, err))
            return None
        inlet = None
    if inlet is None:
        inlet = place(base.create(selectTOP, 'crown_title_in'), 560, 40)
    inlet.viewer = False
    inlet.display = False
    if hasattr(inlet.par, 'outputresolution'):
        choose(inlet.par.outputresolution, 'useinput')
    try:
        inlet.par.top.val = title.path
    except Exception as err:
        print('gif: could not point the title select at %s: %s' % (title.path, err))
        return None
    try:
        chosen = op_path(inlet.par.top.eval())
    except Exception as err:
        print('gif: title select parameter: %s' % err)
        return None
    if chosen != title.path:
        print('gif: title select reads %s, wanted %s.' % (chosen or '(none)', title.path))
        return None
    problems = []
    problems.extend(cook_errors(inlet))
    if looks_like_checker(inlet):
        problems.append('%s is drawing the chequer error picture' % inlet.path)
    try:
        if int(inlet.width) < 2 or int(inlet.height) < 2:
            problems.append('%s is %sx%s' % (inlet.path, inlet.width, inlet.height))
    except Exception as err:
        problems.append('title select size: %s' % err)
    if problems:
        for item in problems:
            print('gif: %s' % item)
        return None
    return inlet


def expose_stack(base, stack):
    """An operator inside crown_vis cannot wire to visual. An Out TOP gives the component an output."""
    outlet = base.op('crown_out')
    if outlet is None:
        outlet = place(base.create(outTOP, 'crown_out'), 840, 200)
    outlet.viewer = False
    outlet.display = False
    if hasattr(outlet.par, 'outputresolution'):
        choose(outlet.par.outputresolution, 'useinput')
    previous = input_owner(outlet, 0)
    if not wire(outlet, stack, 0):
        print('gif: %s did not reach crown_out. %s' % (stack.path, input_report(outlet)))
        return None, previous
    try:
        outlet.cook(force=True)
        base.cook(force=True)
    except Exception as err:
        print('gif: crown_out cook: %s' % err)
    try:
        outs = list(base.outputConnectors)
    except Exception as err:
        print('gif: crown_vis outputs: %s' % err)
        return None, previous
    if len(outs) < 1:
        print('gif: crown_vis did not gain an output from crown_out. visual was not rewired.')
        return None, previous
    problems = []
    problems.extend(cook_errors(outlet))
    if looks_like_checker(outlet):
        problems.append('%s is drawing the chequer error picture' % outlet.path)
    try:
        if int(outlet.width) < 2 or int(outlet.height) < 2:
            problems.append('%s is %sx%s' % (outlet.path, outlet.width, outlet.height))
    except Exception as err:
        problems.append('crown_out size: %s' % err)
    if problems:
        for item in problems:
            print('gif: %s' % item)
        if previous is not None:
            wire(outlet, previous, 0)
        return None, previous
    return base, previous


def restore_out(base, previous):
    if previous is None:
        return
    outlet = base.op('crown_out')
    if outlet is None:
        return
    owner = input_owner(outlet, 0)
    if owner is not None and owner.path == previous.path:
        return
    wire(outlet, previous, 0)


def input_report(node):
    try:
        count = len(list(node.inputConnectors))
    except Exception as err:
        return 'connectors unreadable (%s)' % err
    owners = []
    for index in range(count):
        owner = input_owner(node, index)
        owners.append(owner.path if owner else '(none)')
    return 'connectors=%s %s' % (count, owners)


def node_errors(node):
    try:
        return [str(item) for item in (node.errors() or [])]
    except Exception:
        return []


def dat_path(value):
    path = getattr(value, 'path', None)
    if path:
        return path
    return str(value or '')


def vec_rows(node):
    seq = None
    try:
        seq = node.seq.vec
    except Exception:
        seq = None
    rows = []
    count = 0
    if seq is not None:
        try:
            count = int(seq.numBlocks)
        except Exception:
            count = 0
    if count < 1:
        while hasattr(node.par, 'vec%dname' % count) and count < 32:
            count += 1
    for i in range(count):
        name_par = 'vec%dname' % i
        if not hasattr(node.par, name_par):
            break
        rows.append((i, str(getattr(node.par, name_par) or '')))
    return rows, seq


def bind_named(node, pairs):
    rows, seq = vec_rows(node)
    have = {name: i for i, name in rows if name}
    missing = [name for name, _expr in pairs if name not in have]
    if missing and seq is not None:
        try:
            seq.numBlocks = len(rows) + len(missing)
        except Exception as err:
            print('gif: could not add uniform slots on %s: %s' % (node.path, err))
            return False
        rows, _seq = vec_rows(node)
        seen = set()
        for i, name in rows:
            if name and name in seen:
                setattr(node.par, 'vec%dname' % i, '')
            elif name:
                seen.add(name)
        rows, _seq = vec_rows(node)
        have = {name: i for i, name in rows if name}
    free = [i for i, name in rows if not name]
    fi = 0
    ok = True
    for name, expr in pairs:
        if name in have:
            index = have[name]
            fresh = False
        elif fi < len(free):
            index = free[fi]
            fi += 1
            have[name] = index
            fresh = True
        else:
            print('gif: no free uniform slot for %s on %s' % (name, node.path))
            ok = False
            continue
        name_par = 'vec%dname' % index
        value_par = 'vec%dvaluex' % index
        if not hasattr(node.par, name_par) or not hasattr(node.par, value_par):
            print('gif: %s has no %s.' % (node.path, name_par))
            ok = False
            continue
        current = str(getattr(node.par, name_par) or '')
        if current not in ('', name):
            print('gif: refused to overwrite uniform %s on %s.' % (current, node.path))
            ok = False
            continue
        setattr(node.par, name_par, name)
        getattr(node.par, value_par).expr = expr
        if fresh:
            for suffix in ('valuey', 'valuez', 'valuew'):
                extra = 'vec%d%s' % (index, suffix)
                if hasattr(node.par, extra):
                    getattr(node.par, extra).val = 0
    return ok


def ensure_float(page, name, label, default, lo, hi):
    owner = page.owner
    if hasattr(owner.par, name):
        return getattr(owner.par, name)
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


def destroy_named(parent, names):
    removed = []
    # Downstream TOPs first, then the shader DATs.
    order = []
    for token in ('stack', 'over', 'key', 'movie'):
        for name in names:
            if name.endswith('_shader') or name in order:
                continue
            if token in name:
                order.append(name)
    for name in names:
        if name not in order:
            order.append(name)
    for name in order:
        node = parent.op(name)
        if node is None:
            continue
        try:
            docked = list(node.docked)
        except Exception:
            docked = []
        for extra in docked:
            if extra is None or extra.name in names:
                continue
            try:
                extra.destroy()
            except Exception:
                pass
        path = node.path
        node.destroy()
        removed.append(path)
    return removed


def par_value(par, default):
    try:
        return float(par.eval())
    except Exception:
        pass
    try:
        return float(par)
    except Exception:
        return default


def glsl_version_of(node):
    if node is None or not hasattr(node.par, 'glslversion'):
        return 'glsl460'
    try:
        return str(node.par.glslversion.eval())
    except Exception:
        return str(node.par.glslversion)


def arm_glsl(node, version):
    """Compile on the cook, as a pixel shader. A threaded compile draws the chequer on screen."""
    if hasattr(node.par, 'mode'):
        choose(node.par.mode, 'vertexpixel')
    if version and hasattr(node.par, 'glslversion'):
        try:
            node.par.glslversion = version
        except Exception:
            choose(node.par.glslversion, 'glsl460', 'glsl450', 'glsl440', 'glsl430')
    if hasattr(node.par, 'compilebehavior'):
        choose(node.par.compilebehavior, 'stalluntildone')
    if hasattr(node.par, 'errorbehavior'):
        choose(node.par.errorbehavior, 'showcheckerboard')


def info_hits(node):
    chunks = []
    try:
        docked = list(node.docked)
    except Exception:
        docked = []
    for extra in docked:
        if extra is None or 'info' not in (extra.name or '').lower():
            continue
        try:
            chunks.append(extra.text)
            continue
        except Exception:
            pass
        try:
            rows = []
            for r in range(min(int(extra.numRows), 40)):
                cells = [str(extra[r, c]) for c in range(min(int(extra.numCols), 6))]
                rows.append(' | '.join(cells))
            chunks.append('\n'.join(rows))
        except Exception as err:
            chunks.append('%s info: %s' % (node.path, err))
    hits = []
    for line in '\n'.join(chunks).splitlines():
        low = line.lower()
        if 'error' in low and ('shader' in low or 'syntax' in low or 'undeclared' in low or 'failed' in low):
            hits.append('%s: %s' % (node.path, line.strip()[:240]))
    return hits


def sample_color(node, u, v):
    # u and v are 0-1. x and y would be pixel positions, so 0.5 is the first pixel.
    try:
        return node.sample(u=u, v=v)
    except TypeError:
        return node.sample(u, v)


def looks_like_checker(node):
    """The failed-shader picture is saturated magenta and cyan, with no dark pixels."""
    hot = 0
    dark = 0
    seen = 0
    try:
        for u in (0.15, 0.4, 0.65, 0.9):
            for v in (0.15, 0.4, 0.65, 0.9):
                color = sample_color(node, u, v)
                r, g, b = float(color[0]), float(color[1]), float(color[2])
                seen += 1
                if max(r, g, b) < 0.25:
                    dark += 1
                if max(r, g, b) > 0.75 and min(r, g, b) < 0.2:
                    hot += 1
    except Exception:
        return False
    return seen >= 8 and dark == 0 and hot >= seen - 2


def finish_glsl(node, dat):
    if hasattr(node.par, 'pixeldat'):
        node.par.pixeldat = dat
    problems = []
    problems.extend(cook_errors(node))
    problems.extend(cook_errors(node))
    problems.extend(info_hits(node))
    if looks_like_checker(node):
        problems.append('%s is drawing the chequer error picture' % node.path)
    return problems


def build_layer(base, title, names, scale_par, x_par, y_par, asset_file, key_mode, key_res):
    """Movie, key, and the texel-for-texel stack. Names must be free.

    key_res is visual's size, so visual reads crown_key 1:1. The stack is
    key height plus title_card height, so neither half is squeezed.
    """
    movie_n, key_n, stack_n, key_dat_n, stack_dat_n = names
    key_w, key_h = key_res
    movie = place(base.create(moviefileinTOP, movie_n), 0, 200)
    movie.viewer = False
    movie.display = False
    movie.par.file = asset_file
    if hasattr(movie.par, 'playmode'):
        choose(movie.par.playmode, 'sequential')
    if hasattr(movie.par, 'play'):
        movie.par.play = True
    if hasattr(movie.par, 'speed'):
        movie.par.speed = 1
    if hasattr(movie.par, 'reload'):
        try:
            movie.par.reload.pulse()
        except Exception as err:
            print('gif: gif reload: %s' % err)

    version = glsl_version_of(op(RACK).op('visual'))
    key = place(base.create(glslTOP, key_n), 280, 200)
    key.viewer = False
    key.display = False
    arm_glsl(key, version)
    set_top_res(key, key_w, key_h)
    if hasattr(key.par, 'format'):
        choose(key.par.format, 'rgba8fixed')
    if hasattr(key.par, 'inputfiltertype'):
        # The classic key samples with texture(). The other keys use texelFetch.
        choose(key.par.inputfiltertype, 'linear')
    if not wire(key, movie, 0):
        return movie, key, None, ['%s has no movie input' % key.path]
    key_dat = place(base.create(textDAT, key_dat_n), 0, 0)
    key_dat.text = KEY_SHADER
    if not bind_named(key, [
        ('uGifScale', 'parent().par.Gifscale'),
        ('uGifX', 'parent().par.Gifx'),
        ('uGifY', 'parent().par.Gify'),
        ('uKeyMode', repr(float(key_mode))),
    ]):
        key_dat.text = KEY_SHADER.replace(
            'uniform float uGifScale;', 'const float uGifScale = %.1f;' % par_value(scale_par, 320.0), 1,
        ).replace(
            'uniform float uGifX;', 'const float uGifX = %.3f;' % par_value(x_par, 0.5), 1,
        ).replace(
            'uniform float uGifY;', 'const float uGifY = %.3f;' % par_value(y_par, 0.02), 1,
        ).replace(
            'uniform float uKeyMode;', 'const float uKeyMode = %.1f;' % float(key_mode), 1,
        )
        print('gif: sliders are not wired. Using the values printed below as constants.')

    early = []
    early.extend(cook_errors(movie))
    early.extend(finish_glsl(key, key_dat))
    if early:
        return movie, key, None, early

    stack = place(base.create(glslTOP, stack_n), 560, 200)
    stack.viewer = False
    stack.display = False
    arm_glsl(stack, version)
    set_top_res(stack, key_w, key_h + 272)
    # crown_key keeps its own size. Only the title rows follow title_card.
    # Constants for the key, because gif_key is renamed crown_key later.
    try:
        stack.par.resolutionw.expr = "max(%d, int(op('%s/title_card').par.resolutionw))" % (key_w, RACK)
        stack.par.resolutionh.expr = "%d + int(op('%s/title_card').par.resolutionh)" % (key_h, RACK)
    except Exception as err:
        print('gif: stack size will not follow the title card: %s' % err)
        return movie, key, stack, ['%s size expressions: %s' % (stack.path, err)]
    if hasattr(stack.par, 'format'):
        choose(stack.par.format, 'rgba8fixed')
    if hasattr(stack.par, 'inputfiltertype'):
        choose(stack.par.inputfiltertype, 'nearest', 'linear')
    inlet = bring_title(base, title)
    if inlet is None:
        return movie, key, stack, ['title card could not enter crown_vis']
    if not wire(stack, key, 0) or not wire(stack, inlet, 1):
        return movie, key, stack, ['%s inputs did not stick: %s' % (stack.path, input_report(stack))]
    # Write the shader only after both inputs are connected, so index 1 exists.
    stack_dat = place(base.create(textDAT, stack_dat_n), 280, 0)
    stack_dat.text = STACK_SHADER

    problems = []
    problems.extend(cook_errors(title))
    problems.extend(finish_glsl(stack, stack_dat))
    if any('array index' in item for item in problems):
        stack_dat.text = STACK_SHADER + '\n'
        problems = finish_glsl(stack, stack_dat)
        if problems:
            problems.append(input_report(stack))
    try:
        if int(movie.width) < 2 or int(movie.height) < 2:
            problems.append('%s loaded at %sx%s' % (movie.path, movie.width, movie.height))
    except Exception as err:
        problems.append('movie size: %s' % err)
    # visual finds the title rows by these sizes, so they must hold exactly.
    try:
        want_w = max(key_w, int(title.par.resolutionw))
        want_h = key_h + int(title.par.resolutionh)
        if (int(key.width), int(key.height)) != (key_w, key_h):
            problems.append('%s is %sx%s, wanted %sx%s' % (key.path, key.width, key.height, key_w, key_h))
        if (int(stack.width), int(stack.height)) != (want_w, want_h):
            problems.append('%s is %sx%s, wanted %sx%s' % (
                stack.path, stack.width, stack.height, want_w, want_h))
    except Exception as err:
        problems.append('layer size check: %s' % err)
    return movie, key, stack, problems


def rename_to(node, name):
    if node is None or node.name == name:
        return
    node.name = name


def relink_shaders(base):
    """Renaming a DAT does not update a GLSL TOP's Pixel Shader parameter.
    Without this, crown_key and crown_stack lose their shader, error (red X),
    and pass the raw olive gif straight through to visual."""
    problems = []
    for top_name, dat_name in (('crown_key', 'crown_key_shader'), ('crown_stack', 'crown_stack_shader')):
        node = base.op(top_name)
        dat = base.op(dat_name)
        if node is None or dat is None:
            problems.append('%s or %s is missing after the rename' % (top_name, dat_name))
            continue
        try:
            node.par.pixeldat = dat
        except Exception as err:
            problems.append('%s pixeldat: %s' % (node.path, err))
            continue
        problems.extend(cook_errors(node))
    return problems


def crown_patcher():
    ns = {'CROWN_SHAPE_NO_RUN': True}
    exec(open(r'C:\Users\James\Desktop\TOUCH\crown_shape.py', encoding='utf-8').read(), ns)
    return ns['patch_shader']


def prepare_shader(text):
    """Crown shape, then the lower rest line and the gif mix. Nothing is written here."""
    text = norm(text)
    notes = []
    if len(REST_RE.findall(text)) != 1:
        patched, crown_notes = crown_patcher()(text)
        if patched is None:
            return None, ['the picture is not the terrain shader (%s)' % (crown_notes,)]
        text = patched
        notes.append('crown')
    patched, gif_notes = patch_gif(text)
    if patched is None:
        return None, gif_notes
    return patched, notes + list(gif_notes)


def cook_errors(node):
    problems = []
    try:
        node.cook(force=True)
    except Exception as err:
        problems.append('%s cook: %s' % (node.path, err))
    for err in node_errors(node):
        problems.append('%s: %s' % (node.path, err))
    return problems


def asset_tools():
    """The callback DAT's functions, run here in a separate namespace."""
    ns = {}
    exec(ASSET_CALLBACKS, ns)
    return ns


def music_page(rack):
    for existing in rack.customPages:
        if existing.name == 'Music':
            return existing
    return rack.appendCustomPage('Music')


def chosen_asset_file(rack, tools):
    """The Asset menu's file if it exists, else koth_crown.gif, else the first asset."""
    import os
    name = tools['asset_name'](rack)
    if name and os.path.isfile(os.path.join(ASSET_DIR, name)):
        return os.path.join(ASSET_DIR, name)
    if os.path.isfile(GIF):
        return GIF
    rows = tools['asset_rows']()
    return rows[0][1] if rows else ''


def ensure_asset_pars(rack, current_file):
    """Asset, Asset Key, Reload Assets at the end of the Music page. Values already set stay."""
    import os
    page = music_page(rack)
    created = []
    if not hasattr(rack.par, 'Asset'):
        par = as_par(page.appendMenu('Asset', label='Asset'))
        name = os.path.basename(current_file or GIF)
        par.menuNames = [name]
        par.menuLabels = [name]
        par.default = name
        par.val = name
        created.append('Asset')
    if not hasattr(rack.par, 'Assetkey'):
        par = as_par(page.appendMenu('Assetkey', label='Asset Key'))
        par.menuNames = list(KEY_MODES)
        par.menuLabels = list(KEY_LABELS)
        par.default = 'classic'
        par.val = 'classic'
        created.append('Assetkey')
    else:
        rack.par.Assetkey.menuNames = list(KEY_MODES)
        rack.par.Assetkey.menuLabels = list(KEY_LABELS)
    if not hasattr(rack.par, 'Reloadassets'):
        as_par(page.appendPulse('Reloadassets', label='Reload Assets'))
        created.append('Reloadassets')
    return created


GIF_PARS = (
    ('Gifscale', 'Gif Scale', 320.0, 40.0, 640.0),
    ('Gifx', 'Gif X', 0.5, 0.0, 1.0),
    ('Gify', 'Gif Y', 0.02, 0.0, 0.40),
)


def ensure_rack_gif_pars(rack, base):
    """Gif Scale, X, Y on the Music page too. New ones start at crown_vis's values."""
    page = music_page(rack)
    created = []
    for name, label, default, lo, hi in GIF_PARS:
        if hasattr(rack.par, name):
            continue
        current = par_value(getattr(base.par, name), default) if hasattr(base.par, name) else default
        par = ensure_float(page, name, label, default, lo, hi)
        par.val = current
        created.append(name)
    return created


def link_gif_pars(rack, base):
    """Bind crown_vis's sliders to the Music page ones. Both stay usable and in step.
    crown_key keeps reading parent().par.Gifscale, so its wiring does not change."""
    notes = []
    for name, _label, _default, _lo, _hi in GIF_PARS:
        mine = getattr(base.par, name, None)
        theirs = getattr(rack.par, name, None)
        if mine is None or theirs is None:
            notes.append('%s missing' % name)
            continue
        link = 'parent().par.%s' % name
        try:
            if mine.mode == ParMode.BIND and mine.bindExpr == link:  # noqa: F821
                continue
            mine.bindExpr = link
            mine.mode = ParMode.BIND  # noqa: F821
            if abs(par_value(mine, -1.0) - par_value(theirs, -2.0)) < 1e-6:
                notes.append('%s bound' % name)
                continue
        except Exception as err:
            notes.append('%s bind failed (%s)' % (name, err))
        # Older builds without binding: follow the Music page by expression.
        try:
            mine.expr = link
            mine.mode = ParMode.EXPRESSION  # noqa: F821
            notes.append('%s follows the Music page (expression)' % name)
        except Exception as err:
            notes.append('%s not linked (%s)' % (name, err))
    return notes


def ensure_asset_table(base):
    table = base.op('asset_table')
    if table is None:
        table = place(base.create(tableDAT, 'asset_table'), 0, -200)
        table.viewer = False
    return table


def set_callbacks_active(base, active):
    dat = base.op('asset_callbacks') if base is not None else None
    if dat is not None and hasattr(dat.par, 'active'):
        try:
            dat.par.active = active
        except Exception as err:
            print('gif: asset callbacks active=%s: %s' % (active, err))


def ensure_asset_callbacks(rack, base):
    """Parameter Execute DAT in crown_vis, watching the asset pulses and menus on music_rack."""
    dat = base.op('asset_callbacks')
    if dat is None:
        kind = None
        for name in ('parameterexecuteDAT', 'parexecDAT', 'parexecuteDAT'):
            try:
                kind = eval(name)
                break
            except NameError:
                continue
        if kind is None:
            print('gif: no Parameter Execute DAT type. Asset menus will not react until fixed.')
            return None
        dat = place(base.create(kind, 'asset_callbacks'), 280, -200)
    dat.text = ASSET_CALLBACKS
    try:
        dat.par.op = rack
    except Exception:
        dat.par.op = rack.path
    for name, value in (('pars', 'Asset Assetkey Reloadassets Reloadtracks'),
                        ('custom', True), ('builtin', False), ('valuechange', True),
                        ('onpulse', True), ('valueschanged', False)):
        if hasattr(dat.par, name):
            setattr(dat.par, name, value)
    if hasattr(dat.par, 'active'):
        dat.par.active = True
    return dat


def key_resolution(visual):
    try:
        width, height = int(visual.width), int(visual.height)
    except Exception:
        width, height = 0, 0
    if width < 16 or height < 16:
        width, height = 1280, 720
    return width, height


def uniform_names(node):
    rows, _seq = vec_rows(node)
    return set(name for _i, name in rows if name)


def unbind_named(node, names):
    """Blank uniform slots this run added, so a rollback leaves visual as it was."""
    rows, _seq = vec_rows(node)
    for i, name in rows:
        if name not in names:
            continue
        try:
            setattr(node.par, 'vec%dname' % i, '')
            value = getattr(node.par, 'vec%dvaluex' % i)
            value.expr = ''
            value.mode = ParMode.CONSTANT  # noqa: F821
            value.val = 0
        except Exception as err:
            print('gif: could not clear %s on %s: %s' % (name, node.path, err))


def measured_backdrop(movie):
    """Corner colour of the asset as TouchDesigner delivers it, 0-255."""
    found = []
    for u, v in ((0.01, 0.01), (0.99, 0.01), (0.01, 0.99), (0.99, 0.99)):
        try:
            color = sample_color(movie, u, v)
            found.append([float(color[i]) for i in range(4)])
        except Exception:
            return None
    return [round(sum(c[i] for c in found) / len(found) * 255.0, 1) for i in range(4)]


def check_title_margin(title):
    """The banner draws wherever title_card's alpha is above 0. Its margin must be clear."""
    try:
        corner = sample_color(title, 0.01, 0.01)
        alpha = float(corner[3])
    except Exception as err:
        return 'title_card margin unreadable: %s' % err
    if alpha <= 0.02:
        return 'title_card margin alpha %.2f (clear)' % alpha
    note = 'title_card margin alpha %.2f: the title would cross the sky as a solid rectangle' % alpha
    if hasattr(title.par, 'bgalpha'):
        try:
            before = float(title.par.bgalpha.eval())
            if before > 0.0:
                title.par.bgalpha = 0
                title.cook(force=True)
                after = float(sample_color(title, 0.01, 0.01)[3])
                note += '. bgalpha was %.2f, set to 0, margin alpha now %.2f' % (before, after)
        except Exception as err:
            note += '. bgalpha: %s' % err
    return note


def crown_vis_report(base):
    """Errors anywhere inside crown_vis, and operators no script here creates."""
    lines = []
    try:
        found = base.errors(recurse=True)
    except TypeError:
        found = base.errors()
    except Exception as err:
        found = 'errors() failed: %s' % err
    lines.append('crown_vis.errors(recurse=True): %s' % (found or '(none)'))
    known = set(OWNED) | set(TEMP_NAMES) | set(KEPT)
    for child in base.children:
        if child.name in known:
            continue
        try:
            dock = child.dock
        except Exception:
            dock = None
        if dock is not None and dock.name in known:
            continue
        try:
            errs = str(child.errors() or '')
        except Exception as err:
            errs = 'errors() failed: %s' % err
        lines.append('not made by add_gif.py: %s %s%s' % (
            child.path, child.OPType, ('  ERRORS %s' % errs) if errs else ''))
        lines.append("  remove it with: op('%s').destroy()" % child.path)
    return lines


def install_gif():
    rack = op(RACK)
    base = rack.op('crown_vis') if rack is not None else None
    set_callbacks_active(base, False)
    try:
        _install_gif()
    finally:
        rack = op(RACK)
        base = rack.op('crown_vis') if rack is not None else None
        if base is not None and hasattr(rack.par, 'Asset'):
            ensure_asset_callbacks(rack, base)


def _install_gif():
    rack = op(RACK)
    if rack is None:
        print('gif: %s is missing. Nothing was changed.' % RACK)
        return
    visual = rack.op('visual')
    shader = rack.op('visual_shader')
    preview = rack.op('preview')
    title = rack.op('title_card')
    if visual is None or shader is None or preview is None or title is None:
        print('gif: need visual, visual_shader, preview, and title_card. Nothing was changed.')
        return

    try:
        bound = visual.par.pixeldat.eval()
    except Exception as err:
        print('gif: could not read the shader parameter: %s. Nothing was changed.' % err)
        return
    if dat_path(bound) != shader.path:
        print('gif: visual is not reading visual_shader. Nothing was changed.')
        print('gif: pixeldat is %s' % dat_path(bound))
        return

    preview_src = input_owner(preview, 0)
    if preview_src is None or preview_src.path != visual.path:
        print('gif: preview is not on visual. Nothing was changed.')
        print('gif: preview input is %s' % (preview_src.path if preview_src else '(none)'))
        return

    try:
        n_inputs = len(list(visual.inputConnectors))
    except Exception as err:
        print('gif: could not read visual inputs: %s. Nothing was changed.' % err)
        return
    if n_inputs < 3:
        print('gif: visual has %s inputs. Nothing was changed.' % n_inputs)
        return

    src0 = input_owner(visual, 0)
    src1 = input_owner(visual, 1)
    src2 = input_owner(visual, 2)
    if src2 is None and wire(visual, title, 2):
        src2 = input_owner(visual, 2)
        print('gif: visual input 2 was empty. It is back on the title card.')
    vis_path = RACK + '/crown_vis'
    allowed = (
        title.path,
        vis_path,
        vis_path + '/crown_stack',
        vis_path + '/gif_stack',
    )
    if src0 is None or src1 is None:
        print('gif: visual inputs 0 and 1 are not both connected. Nothing was changed.')
        return
    if src2 is None or src2.path not in allowed:
        print('gif: visual input 2 is not title_card. Nothing was changed.')
        print('gif: visual input 2 is %s' % (src2.path if src2 else '(none)'))
        return

    tools = asset_tools()
    asset_file = chosen_asset_file(rack, tools)
    if not asset_file:
        print('gif: no gif, png, jpg, mp4, or mov in %s. Nothing was changed.' % ASSET_DIR)
        return

    before = norm(shader.text)
    patched, notes = prepare_shader(before)
    if patched is None:
        print('gif: visual_shader could not take the gif. Nothing was changed.')
        for item in notes:
            print('gif: %s' % item)
        return

    base = rack.op('crown_vis')
    if base is None:
        base = place(rack.create(baseCOMP, 'crown_vis'), 2100, 360)
    base.viewer = False
    base.display = False

    page = None
    for existing in base.customPages:
        if existing.name == 'Gif':
            page = existing
            break
    if page is None:
        page = base.appendCustomPage('Gif')
    # Gif Scale: the asset's longer side in pixels of a 1280x720 frame.
    # 320 is 1:1 for koth_crown.gif and 640 is exactly 2x.
    scale_par = ensure_float(page, 'Gifscale', 'Gif Scale', 320.0, 40.0, 640.0)
    x_par = ensure_float(page, 'Gifx', 'Gif X', 0.5, 0.0, 1.0)
    y_par = ensure_float(page, 'Gify', 'Gif Y', 0.02, 0.0, 0.40)

    # Asset menus on the Music page. Values already chosen stay as they are.
    import os
    created_pars = ensure_asset_pars(rack, asset_file)
    created_pars += ensure_rack_gif_pars(rack, base)
    link_notes = link_gif_pars(rack, base)
    ensure_asset_table(base)
    tools['refresh_assets'](rack, base)
    asset_file = chosen_asset_file(rack, tools)
    asset_name = os.path.basename(asset_file)
    key_name = tools['stored_keys'](base).get(asset_name, tools['default_key'](asset_name))
    if str(rack.par.Assetkey.eval()) != key_name:
        rack.par.Assetkey = key_name
    key_mode = KEY_MODES.index(key_name)
    key_res = key_resolution(visual)

    # The live picture keeps its current input 2 until the new stack has cooked.
    live_stack = src2.path != title.path
    removed = []
    if live_stack:
        removed.extend(destroy_named(base, TEMP_NAMES))
        names = TEMP_NAMES
    else:
        removed.extend(destroy_named(base, OWNED))
        names = CROWN_NAMES

    _movie, _key, stack, layer_problems = build_layer(
        base, title, names, scale_par, x_par, y_par, asset_file, key_mode, key_res)
    if layer_problems or stack is None:
        if live_stack:
            destroy_named(base, TEMP_NAMES)
        print('gif: the gif layer failed. visual_shader and preview were not changed.')
        now2 = input_owner(visual, 2)
        print('gif: visual input 2 is %s' % (now2.path if now2 else '(none)'))
        for item in layer_problems:
            print('gif ERROR: %s' % item)
        return

    # crown_stack stays inside crown_vis. visual wires to the component output.
    shown, out_prev = expose_stack(base, stack)
    if shown is None:
        if live_stack:
            restore_out(base, out_prev)
            destroy_named(base, TEMP_NAMES)
        print('gif: the stack stayed inside crown_vis. visual_shader and preview were not changed.')
        now2 = input_owner(visual, 2)
        print('gif: visual input 2 is %s' % (now2.path if now2 else '(none)'))
        return

    # Keep the spectrum and the level inputs. Then point input 2 at crown_vis.
    saved_compile = None
    if hasattr(visual.par, 'compilebehavior'):
        try:
            saved_compile = str(visual.par.compilebehavior.eval())
        except Exception:
            saved_compile = str(visual.par.compilebehavior)
        choose(visual.par.compilebehavior, 'stalluntildone')

    def park_inputs(third):
        ok = wire(visual, src0, 0) and wire(visual, src1, 1) and wire(visual, third, 2)
        return ok

    def restore_compile():
        if saved_compile and hasattr(visual.par, 'compilebehavior'):
            try:
                visual.par.compilebehavior.val = saved_compile
            except Exception:
                choose(visual.par.compilebehavior, saved_compile)

    if not park_inputs(shown):
        park_inputs(src2)
        restore_out(base, out_prev)
        restore_compile()
        print('gif: visual inputs could not be set. Shader text was not changed.')
        print('gif: visual input 2 is %s' % (
            input_owner(visual, 2).path if input_owner(visual, 2) else '(none)'))
        if live_stack:
            destroy_named(base, TEMP_NAMES)
        return

    held0 = input_owner(visual, 0)
    held1 = input_owner(visual, 1)
    if held0 is None or held1 is None or held0.path != src0.path or held1.path != src1.path:
        park_inputs(src2)
        restore_out(base, out_prev)
        restore_compile()
        print('gif: wiring the gif dropped an audio input. Those inputs are back. Shader text was not changed.')
        if live_stack:
            destroy_named(base, TEMP_NAMES)
        return

    # visual finds crown_key and title_card inside crown_stack by these sizes.
    had_uniforms = uniform_names(visual)
    layout_ok = bind_named(visual, [
        ('uGifKeyW', '%d' % key_res[0]),
        ('uGifKeyH', '%d' % key_res[1]),
        ('uGifCardW', "op('title_card').par.resolutionw"),
        ('uGifCardH', "op('title_card').par.resolutionh"),
    ])
    added_uniforms = [name for name in LAYOUT_UNIFORMS if name not in had_uniforms]

    shader.text = patched
    problems = []
    if not layout_ok:
        problems.append('%s could not take the crown_stack layout uniforms' % visual.path)
    problems.extend(cook_errors(visual))
    problems.extend(cook_errors(visual))
    problems.extend(info_hits(visual))
    if looks_like_checker(visual):
        problems.append('%s is drawing the chequer error picture' % visual.path)
    if problems:
        shader.text = before
        unbind_named(visual, added_uniforms)
        park_inputs(src2)
        restore_out(base, out_prev)
        try:
            visual.cook(force=True)
            visual.cook(force=True)
        except Exception:
            pass
        restore_compile()
        if live_stack:
            destroy_named(base, TEMP_NAMES)
        print('gif: the terrain shader failed. Previous text is back.')
        now2 = input_owner(visual, 2)
        print('gif: visual input 2 is %s' % (now2.path if now2 else '(none)'))
        for item in problems:
            print('gif ERROR: %s' % item)
        try:
            print('visual.errors(): %s' % (list(visual.errors() or []) or '(none)'))
        except Exception:
            pass
        return
    restore_compile()

    if live_stack:
        removed.extend(destroy_named(base, OWNED))
        rename_to(base.op('gif_movie'), 'crown_movie')
        rename_to(base.op('gif_key'), 'crown_key')
        rename_to(base.op('gif_stack'), 'crown_stack')
        rename_to(base.op('gif_key_shader'), 'crown_key_shader')
        rename_to(base.op('gif_stack_shader'), 'crown_stack_shader')
        # Pixel Shader still names gif_*_shader after the rename. Point it again.
        for item in relink_shaders(base):
            print('gif ERROR: %s' % item)

    in0 = input_owner(visual, 0)
    in1 = input_owner(visual, 1)
    in2 = input_owner(visual, 2)
    preview_now = input_owner(preview, 0)
    errs = node_errors(visual)
    print('')
    print('visual.errors(): %s' % (errs or '(none)'))
    print('preview left on %s' % (preview_now.path if preview_now else '(none)'))
    print('visual input 0 %s' % (in0.path if in0 else '(none)'))
    print('visual input 1 %s' % (in1.path if in1 else '(none)'))
    print('visual input 2 was %s' % src2.path)
    print('visual input 2 is %s' % (in2.path if in2 else '(none)'))
    print('REST_LIFT is %.2f. Resting ends sit near y=0.31, centre near y=0.39.' % REST_LIFT)
    print('Gif Scale %s, Gif X %s, Gif Y %s on %s.' % (
        par_value(scale_par, 320.0), par_value(x_par, 0.5), par_value(y_par, 0.02), base.path))
    print('Shader notes: %s.' % ', '.join(notes))
    movie_now = base.op('crown_movie')
    key_now = base.op('crown_key')
    stack_now = base.op('crown_stack')
    try:
        print('Asset %s, key %s. Source %sx%s, crown_key %sx%s, crown_stack %sx%s, title_card %sx%s.' % (
            asset_name, key_name, movie_now.width, movie_now.height, key_now.width, key_now.height,
            stack_now.width, stack_now.height, title.width, title.height))
    except Exception as err:
        print('gif: sizes unreadable: %s' % err)
    if created_pars:
        print('Added %s to the Music page of %s.' % (', '.join(created_pars), rack.path))
    if link_notes:
        print('Gif sliders: %s.' % ', '.join(link_notes))
    if movie_now is not None:
        seen = measured_backdrop(movie_now)
        print('Corner colour as delivered (0-255, RGBA): %s. In the file koth_crown.gif it is about 38 39 1.' % (
            seen if seen else '(unreadable)'))
    print(check_title_margin(title))
    for line in crown_vis_report(base):
        print(line)
    if removed:
        print('Removed %s.' % ', '.join(removed))
    leftovers = [
        child.path for child in rack.children
        if child.name != 'crown_vis' and child.name.startswith('crown')
    ]
    if leftovers:
        print('Left in place: %s.' % ', '.join(leftovers))
    same0 = (in0.path if in0 else '') == (src0.path if src0 else '')
    same1 = (in1.path if in1 else '') == (src1.path if src1 else '')
    if not same0 or not same1:
        print('gif: inputs 0 and 1 changed. They were %s and %s.' % (
            src0.path if src0 else '(none)', src1.path if src1 else '(none)'))
    print('')


def self_check():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'crown_shape_for_gif', r'C:\Users\James\Desktop\TOUCH\crown_shape.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    src = open(r'C:\Users\James\Desktop\TOUCH\build_music_rack.py', encoding='utf-8').read()
    crown, _crown_notes = mod.patch_shader(src)
    crown30 = crown.replace(
        'const float REST_LIFT = 0.20;', 'const float REST_LIFT = 0.30;', 1)
    patched, notes = patch_gif(crown30)
    again, notes2 = patch_gif(patched) if patched else (None, None)
    bare, bare_notes = patch_gif(src)
    full, full_notes = prepare_shader(src)
    full_again, _full_notes2 = prepare_shader(full) if full else (None, None)
    # A shader patched by the half-and-half version moves to the new layout.
    legacy = patched.replace(SIZE_LINE, SIZE_LEGACY, 1) if patched else None
    migrated, migrated_notes = patch_gif(legacy) if legacy else (None, None)
    me_text = open(r'C:\Users\James\Desktop\TOUCH\add_gif.py', encoding='utf-8').read()
    tools = asset_tools()
    rows = tools['asset_rows']()
    try:
        compile(ASSET_CALLBACKS, 'asset_callbacks', 'exec')
        callbacks_ok = True
    except SyntaxError as err:
        print('asset callbacks: %s' % err)
        callbacks_ok = False
    classic = (
        'float near = smoothstep(0.10, 0.18, d) * smoothstep(0.10, 0.22, luma);',
        'float vivid = smoothstep(0.22, 0.42, luma) * smoothstep(0.18, 0.36, chroma);',
        'float a = max(near, vivid) * inside;',
        'return vec4(s.rgb, a);',
        'vec3 olive = vec3(39.0, 40.0, 2.0) / 255.0;',
    )
    assets_ok = (
        callbacks_ok
        and 'koth_crown.gif' in [name for name, _full in rows]
        and tools['default_key']('x.png') == 'none'
        and tools['default_key']('koth_crown.gif') == 'classic'
        and tuple(tools['KEY_MODES']) == KEY_MODES
        and len(KEY_LABELS) == len(KEY_MODES)
        and all(line in KEY_SHADER for line in classic)
        and 'uniform float uKeyMode;' in KEY_SHADER
        and 'textureSize(sTD2DInputs[0], 0)' in KEY_SHADER
        and 'texelFetch(sTD2DInputs[1], q, 0)' in STACK_SHADER
        and 'vUV.y * 2.0' not in STACK_SHADER
    )
    ok = (
        crown is not None
        and patched is not None
        and again == patched
        and bare is None
        and full is not None
        and full_again == full
        and 'float yl = base + crownOffset(xL, z, al) + al * hs;' in full
        and full.count(GIF_BEGIN) == 1
        and 'crown' in full_notes
        and patched.count('const float REST_LIFT = 0.20;') == 1
        and 'const float REST_LIFT = 0.30' not in patched
        and patched.count(GIF_BEGIN) == 1
        and patched.count(SIZE_NEW) == 1
        and 'size.y /= 2;' not in patched
        and migrated == patched
        and 'title size from half stack' in migrated_notes
        and full.count(SIZE_NEW) == 1
        and all(('uniform float %s;' % name) in patched for name in LAYOUT_UNIFORMS)
        and assets_ok
        and 'clamp(texUV, 0.0, 1.0)).a * inside' not in patched
        and '0.5 + texUV.y * 0.5' in patched
        and 'sTD2DInputs[3]' not in patched
        and 'float yl = base + crownOffset(xL, z, al) + al * hs;' in patched
        and 'return pow(clamp(v, 0.0, 1.0), 1.35)' in patched
        and 'fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));' in patched
        and again.count('// GIF_TITLE begin') == 1
        and 'create(selectTOP' in me_text
        and 'create(outTOP' in me_text
        and ('for item in relink_shaders' + '(base):') in me_text
        and ('wire(stack, ' + 'title') not in me_text
    )
    print('gif self-check: %s' % ('ok' if ok else 'FAILED'))
    print('assets in %s: %s' % (ASSET_DIR, ', '.join(name for name, _full in rows) or '(none)'))
    if not ok:
        print('notes %s again %s bare %s full %s migrated %s assets %s' % (
            notes, notes2, bare_notes, full_notes, migrated_notes, assets_ok))
    return ok


if inside_td():
    install_gif()
else:
    print('Run this inside the TouchDesigner textport:')
    print("  exec(open(r'C:\\Users\\James\\Desktop\\TOUCH\\add_gif.py', encoding='utf-8').read())")
    self_check()
