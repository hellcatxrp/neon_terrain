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

import re

GIF = r'C:\Users\James\Desktop\TOUCH\assets\koth_crown.gif'
RACK = '/project1/music_rack'
REST_LIFT = 0.20

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
float titleGlyph(vec2 texUV)
{
    float inside = step(0.0, texUV.x) * step(texUV.x, 1.0) * step(0.0, texUV.y) * step(texUV.y, 1.0);
    // Title card lives in the top half of crown_stack.
    vec2 stacked = vec2(texUV.x, 0.5 + texUV.y * 0.5);
    ivec2 titleSize = textureSize(sTD2DInputs[2], 0);
    float seam = 0.5 / max(float(titleSize.y), 1.0);
    stacked.y = max(stacked.y, 0.5 + seam);
    return texture(sTD2DInputs[2], clamp(stacked, 0.0, 1.0)).a * inside;
}
// GIF_TITLE end
'''
SIZE_OLD = '    ivec2 size = textureSize(sTD2DInputs[2], 0);\n'
SIZE_NEW = (
    '    ivec2 size = textureSize(sTD2DInputs[2], 0);\n'
    '    size.y /= 2; // top half of crown_stack is the title card\n'
)
GRAIN = '    col += grain * 0.018;\n'
GIF_BEGIN = '// GIF_UNDER begin'
GIF_END = '// GIF_UNDER end'
GIF_BLOCK = '''    col += grain * 0.018;
    // GIF_UNDER begin
    // Keyed crown is the bottom half of input 2. It shows only in dark pixels.
    {
        vec2 gifUV = vec2(vUV.x, vUV.y * 0.5);
        ivec2 stackSize = textureSize(sTD2DInputs[2], 0);
        float gifSeam = 0.5 / max(float(stackSize.y), 1.0);
        gifUV.y = min(gifUV.y, 0.5 - gifSeam);
        vec4 gifPix = texture(sTD2DInputs[2], gifUV);
        float gifLuma = max(col.r, max(col.g, col.b));
        float gifUnder = 1.0 - smoothstep(0.05, 0.18, gifLuma);
        col = mix(col, gifPix.rgb, clamp(gifPix.a * gifUnder, 0.0, 1.0));
    }
    // GIF_UNDER end
'''

KEY_SHADER = r'''layout(location = 0) out vec4 fragColor;
uniform float uGifScale;
uniform float uGifX;
uniform float uGifY;

// Place the gif in the 1280x720 frame and drop the flat olive field.
// The vivid term still keeps the crystal if the file is read as linear.
void main()
{
    vec2 frame = vec2(1280.0, 720.0);
    float sideX = uGifScale / frame.x;
    float sideY = uGifScale / frame.y;
    float left = uGifX - sideX * 0.5;
    vec2 local = vec2(
        (vUV.x - left) / max(sideX, 1e-4),
        (vUV.y - uGifY) / max(sideY, 1e-4));
    float inside = step(0.0, local.x) * step(local.x, 1.0)
        * step(0.0, local.y) * step(local.y, 1.0);
    vec4 s = texture(sTD2DInputs[0], clamp(local, 0.0, 1.0));
    vec3 olive = vec3(39.0, 40.0, 2.0) / 255.0;
    float d = distance(s.rgb, olive);
    float luma = max(s.r, max(s.g, s.b));
    float chroma = luma - min(s.r, min(s.g, s.b));
    float near = smoothstep(0.10, 0.18, d) * smoothstep(0.10, 0.22, luma);
    float vivid = smoothstep(0.22, 0.42, luma) * smoothstep(0.18, 0.36, chroma);
    float a = max(near, vivid) * inside;
    fragColor = TDOutputSwizzle(vec4(s.rgb, a));
}
'''

STACK_SHADER = r'''layout(location = 0) out vec4 fragColor;

// Input 0 is the placed gif. Input 1 is title_card.
// Both are sampled on every pixel. Bottom half is the gif, top half the title.
void main()
{
    vec4 gif = texture(sTD2DInputs[0], vec2(vUV.x, clamp(vUV.y * 2.0, 0.0, 1.0)));
    vec4 title = texture(sTD2DInputs[1], vec2(vUV.x, clamp((vUV.y - 0.5) * 2.0, 0.0, 1.0)));
    float top = step(0.5, vUV.y);
    fragColor = TDOutputSwizzle(mix(gif, title, top));
}
'''

OWNED = (
    'crown_over', 'crown_stack', 'crown_key', 'crown_movie',
    'crown_over_shader', 'crown_stack_shader', 'crown_key_shader',
)
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
    if 'size.y /= 2;' in text and text.count('size.y /= 2;') != 1:
        reasons.append('title half-height count is wrong')
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
    if 'size.y /= 2;' not in text:
        text = text.replace(SIZE_OLD, SIZE_NEW, 1)
        notes.append('title size')
    else:
        notes.append('title size kept')
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
    if text.count(GIF_BEGIN) != 1 or text.count('size.y /= 2;') != 1:
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


def build_layer(base, title, names, scale_par, x_par, y_par):
    """Movie, olive key, and the two-half stack. Names must be free."""
    movie_n, key_n, stack_n, key_dat_n, stack_dat_n = names
    movie = place(base.create(moviefileinTOP, movie_n), 0, 200)
    movie.viewer = False
    movie.display = False
    movie.par.file = GIF
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
    set_top_res(key, 1280, 720)
    if hasattr(key.par, 'format'):
        choose(key.par.format, 'rgba8fixed')
    if hasattr(key.par, 'inputfiltertype'):
        choose(key.par.inputfiltertype, 'linear')
    if not wire(key, movie, 0):
        return movie, key, None, ['%s has no movie input' % key.path]
    key_dat = place(base.create(textDAT, key_dat_n), 0, 0)
    key_dat.text = KEY_SHADER
    if not bind_named(key, [
        ('uGifScale', 'parent().par.Gifscale'),
        ('uGifX', 'parent().par.Gifx'),
        ('uGifY', 'parent().par.Gify'),
    ]):
        key_dat.text = KEY_SHADER.replace(
            'uniform float uGifScale;\nuniform float uGifX;\nuniform float uGifY;\n',
            'const float uGifScale = %.1f;\nconst float uGifX = %.3f;\nconst float uGifY = %.3f;\n' % (
                par_value(scale_par, 210.0), par_value(x_par, 0.5), par_value(y_par, 0.02)),
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
    set_top_res(stack, 2048, 512)
    try:
        stack.par.resolutionw.expr = "int(op('%s/title_card').par.resolutionw)" % RACK
        stack.par.resolutionh.expr = "int(op('%s/title_card').par.resolutionh) * 2" % RACK
    except Exception as err:
        print('gif: stack size will not follow the title card: %s' % err)
    if hasattr(stack.par, 'format'):
        choose(stack.par.format, 'rgba8fixed')
    if hasattr(stack.par, 'inputfiltertype'):
        choose(stack.par.inputfiltertype, 'linear')
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
    return movie, key, stack, problems


def rename_to(node, name):
    if node is None or node.name == name:
        return
    node.name = name


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


def install_gif():
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

    try:
        import os
        gif_ok = os.path.isfile(GIF)
    except Exception:
        gif_ok = False
    if not gif_ok:
        print('gif: missing %s. Nothing was changed.' % GIF)
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
    scale_par = ensure_float(page, 'Gifscale', 'Gif Scale', 210.0, 40.0, 640.0)
    x_par = ensure_float(page, 'Gifx', 'Gif X', 0.5, 0.0, 1.0)
    y_par = ensure_float(page, 'Gify', 'Gif Y', 0.02, 0.0, 0.40)

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
        base, title, names, scale_par, x_par, y_par)
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

    shader.text = patched
    problems = []
    problems.extend(cook_errors(visual))
    problems.extend(cook_errors(visual))
    problems.extend(info_hits(visual))
    if looks_like_checker(visual):
        problems.append('%s is drawing the chequer error picture' % visual.path)
    if problems:
        shader.text = before
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
        par_value(scale_par, 210.0), par_value(x_par, 0.5), par_value(y_par, 0.02), base.path))
    print('Shader notes: %s.' % ', '.join(notes))
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
        and patched.count('size.y /= 2;') == 1
        and 'clamp(texUV, 0.0, 1.0)).a * inside' not in patched
        and '0.5 + texUV.y * 0.5' in patched
        and 'sTD2DInputs[3]' not in patched
        and 'float yl = base + crownOffset(xL, z, al) + al * hs;' in patched
        and 'return pow(clamp(v, 0.0, 1.0), 1.35)' in patched
        and 'fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));' in patched
        and again.count('// GIF_TITLE begin') == 1
        and 'create(selectTOP' in open(r'C:\Users\James\Desktop\TOUCH\add_gif.py', encoding='utf-8').read()
        and 'create(outTOP' in open(r'C:\Users\James\Desktop\TOUCH\add_gif.py', encoding='utf-8').read()
        and ('wire(stack, ' + 'title') not in open(r'C:\Users\James\Desktop\TOUCH\add_gif.py', encoding='utf-8').read()
    )
    print('gif self-check: %s' % ('ok' if ok else 'FAILED'))
    if not ok:
        print('notes %s again %s bare %s full %s' % (notes, notes2, bare_notes, full_notes))
    return ok


if inside_td():
    install_gif()
else:
    print('Run this inside the TouchDesigner textport:')
    print("  exec(open(r'C:\\Users\\James\\Desktop\\TOUCH\\add_gif.py', encoding='utf-8').read())")
    self_check()
