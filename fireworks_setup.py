# Fireworks in the open sky of /project1/music_rack, behind the scrolling title.
# Adds a Fireworks toggle and a Fireworks Intensity slider to the Music page.
# Does not rewire preview, and does not touch the audio path or the title.
#
# Open C:\Users\James\Desktop\TOUCH\NewProject.8.toe first, then the Textport:
#   exec(open(r'C:\Users\James\Desktop\TOUCH\fireworks_setup.py', encoding='utf-8').read())
#
# Undo:
#   exec(open(r'C:\Users\James\Desktop\TOUCH\fireworks_undo.py', encoding='utf-8').read())
#
# Running this file again replaces the marked shader blocks. It does not
# reset the toggle or the intensity if they are already there.

RACK = '/project1/music_rack'
SETUP_PATH = r'C:\Users\James\Desktop\TOUCH\fireworks_setup.py'
UNDO_PATH = r'C:\Users\James\Desktop\TOUCH\fireworks_undo.py'
BUILDER = r'C:\Users\James\Desktop\TOUCH\build_music_rack.py'
CROWN_PATH = r'C:\Users\James\Desktop\TOUCH\crown_shape.py'

UNI_BEGIN = '// FIREWORKS_UNIFORMS begin'
UNI_END = '// FIREWORKS_UNIFORMS end'
FUNC_BEGIN = '// FIREWORKS_FUNC begin'
FUNC_END = '// FIREWORKS_FUNC end'
CALL_BEGIN = '    // FIREWORKS_CALL begin'
CALL_END = '    // FIREWORKS_CALL end'

TITLE_ANCHOR = 'uniform float uTitleStart; // wall-clock time of the last Title Animation edit\n'
TITLE_ANCHOR_SHORT = 'uniform float uTitleStart;\n'
MAIN_ANCHOR = 'void main()\n'
CALL_ANCHOR = '    // Terrain, front to back. Each ridge\'s black fill hides the rows behind it.\n'

FADE_SECONDS = 0.75
SHELLS = 7

UNI_BLOCK = '''// FIREWORKS_UNIFORMS begin
uniform float uFireOn;    // Fireworks toggle, 1 while on
uniform float uFireEdge;  // wall-clock time of the last toggle change; 0 before the first
uniform float uFireGain;  // Fireworks Intensity, 0..2
// FIREWORKS_UNIFORMS end
'''

FUNC_BLOCK = '''// FIREWORKS_FUNC begin
// Fade is 0 before the first toggle, rises for 0.75s after it is turned on,
// and falls for 0.75s after it is turned off. The shell loop lives in
// fireworksSky, which the call site skips entirely while this is 0.
float fireFade()
{
    if (uFireEdge <= 0.0 && uFireOn < 0.5) {
        return 0.0;
    }
    float age = uClock - uFireEdge;
    float t = clamp(age / 0.75, 0.0, 1.0);
    if (uFireOn >= 0.5) {
        return t;
    }
    return 1.0 - t;
}

float fireHash(float n)
{
    return hash21(vec2(n, n + 2.718));
}

vec3 fireRise(vec2 p, vec2 launch, vec2 apex, float t, vec3 ink)
{
    float curve = sin(t * 3.14159265) * 0.02;
    vec2 head = mix(launch, apex, t);
    head.x += curve;
    float tailT = max(t - 0.16, 0.0);
    vec2 tail = mix(launch, apex, tailT);
    tail.x += sin(tailT * 3.14159265) * 0.02;
    float trail = exp(-segDist(p, tail, head) * 90.0);
    float core = exp(-length(p - head) * 55.0);
    vec3 hot = mix(ink, vec3(1.0, 0.96, 0.88), 0.45);
    return hot * (trail * 0.65 + core * 1.7) * (1.0 - t * 0.15);
}

vec3 fireBurst(vec2 p, vec2 origin, float t, float seed, vec3 ink)
{
    vec2 d = p - origin;
    float droop = mix(0.05, 0.18, fireHash(seed + 5.0));
    d.y += droop * t * t;
    float r = length(d);
    float reach = mix(0.09, 0.18, fireHash(seed + 3.0));
    float ang = atan(d.y, d.x);
    float spokes = mix(12.0, 20.0, fireHash(seed + 6.0));
    float turn = 6.2831853 / spokes;
    float slot = floor((ang + 3.14159265) / turn);
    float a0 = (slot + 0.5) * turn - 3.14159265;
    float jitter = hash21(vec2(slot, seed));
    float arm = reach * t * mix(0.58, 1.0, jitter);
    vec2 dir = vec2(cos(a0), sin(a0));
    float along = dot(d, dir);
    float lateral = length(d - dir * along);
    float onArm = step(0.0, along) * step(along, arm + 0.004);
    float streak = exp(-lateral * 70.0) * onArm;
    float head = exp(-length(d - dir * arm) * 48.0);
    float flash = exp(-r * 16.0) * (1.0 - smoothstep(0.0, 0.22, t));
    float ring = exp(-abs(r - reach * t) * 36.0) * (1.0 - t);
    float life = (1.0 - t) * (0.45 + 0.55 * jitter);
    float tw = 0.78 + 0.22 * sin(uClock * 28.0 + slot + seed);
    vec3 hot = mix(ink, vec3(1.0, 0.94, 0.78), 0.58);
    return hot * (streak * 0.55 + head * tw * 1.8 + flash * 1.15 + ring * 0.28) * life;
}

vec3 fireworksSky(vec2 p, float horizon, vec3 inkA, vec3 inkB, float kick)
{
    if (p.y < horizon) {
        return vec3(0.0);
    }
    vec3 sum = vec3(0.0);
    for (int i = 0; i < 7; i++) {
        float fi = float(i);
        float seed = fi + 1.0;
        float period = 1.65 + fireHash(seed + 4.0) * 1.25;
        float phase = fract((uClock + fireHash(seed) * 17.0) / period);
        float x = mix(-0.62, 0.62, fireHash(seed + 8.0));
        float y = mix(horizon + 0.10, 0.92, fireHash(seed + 12.0));
        vec2 apex = vec2(x, y);
        vec2 launch = vec2(x * 0.35, horizon + 0.008);
        vec3 ink = mix(inkA, inkB, fireHash(seed + 16.0));
        float gold = step(0.62, fireHash(seed + 21.0));
        ink = mix(ink, vec3(1.0, 0.74, 0.30), gold * 0.72);
        if (phase < 0.18) {
            sum += fireRise(p, launch, apex, phase / 0.18, ink);
        } else if (phase < 0.62) {
            sum += fireBurst(p, apex, (phase - 0.18) / 0.44, seed, ink);
        }
    }
    if (kick > 0.04) {
        float slot = floor(uClock * 0.5);
        float kx = mix(-0.48, 0.48, hash21(vec2(slot, 3.2)));
        float ky = mix(horizon + 0.14, 0.86, hash21(vec2(slot, 8.4)));
        vec3 ink = mix(inkA, vec3(1.0, 0.86, 0.45), 0.55);
        sum += fireBurst(p, vec2(kx, ky), clamp(1.0 - kick, 0.0, 1.0), slot + 20.0, ink) * (0.4 + kick);
    }
    float lift = smoothstep(horizon, horizon + 0.02, p.y);
    return sum * 0.65 * lift;
}
// FIREWORKS_FUNC end
'''

CALL_BLOCK = '''    // FIREWORKS_CALL begin
    {
        float fireNow = fireFade();
        // fireNow and uFireGain are uniforms, so this branch is the same for every pixel.
        // While the fade is 0 the shell loop inside fireworksSky is not called.
        if (fireNow > 0.0 && uFireGain > 0.0) {
            if (p.y >= horizon) {
                sky += fireworksSky(p, horizon, cA, cB, kick) * fireNow * uFireGain;
            }
        }
    }
    // FIREWORKS_CALL end
'''

UNIFORMS = (
    ('uFireOn', 'parent().par.Fireworks'),
    ('uFireEdge', "op('fireworks_edge')[0]"),
    ('uFireGain', 'parent().par.Fireworksintensity'),
)

EDGE_CALLBACKS = r'''def onValueChange(par, prev):
    if par.name != 'Fireworks':
        return
    edge = par.owner.op('fireworks_edge')
    if edge is None:
        return
    now = absTime.seconds
    if hasattr(edge.par, 'const0value'):
        edge.par.const0value = now
    elif hasattr(edge.par, 'value0'):
        edge.par.value0 = now
    try:
        edge.cook(force=True)
    except Exception:
        pass
    return


def onValuesChanged(changes):
    for change in changes:
        onValueChange(change.par, getattr(change, 'prev', None))
    return


def onPulse(par):
    return


def onExpressionChange(par, prev):
    return


def onExportChange(par, prev):
    return
'''


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


def apply_block(text, begin, end, block, anchor, mode):
    found = replace_span(text, begin, end, block)
    if found is not None:
        return found, 'updated'
    if not anchor or text.count(anchor) != 1:
        return text, 'missing'
    if mode == 'after':
        inserted = anchor + block
    elif mode == 'before':
        inserted = block + anchor
    else:
        return text, 'missing'
    return text.replace(anchor, inserted, 1), 'inserted'


def title_anchor(text):
    if text.count(TITLE_ANCHOR) == 1:
        return TITLE_ANCHOR
    if text.count(TITLE_ANCHOR_SHORT) == 1:
        return TITLE_ANCHOR_SHORT
    return None


def patch_shader(text):
    text = norm(text)
    anchor = title_anchor(text)
    text, n_uni = apply_block(text, UNI_BEGIN, UNI_END, UNI_BLOCK, anchor, 'after')
    text, n_func = apply_block(text, FUNC_BEGIN, FUNC_END, FUNC_BLOCK, MAIN_ANCHOR, 'before')
    text, n_call = apply_block(text, CALL_BEGIN, CALL_END, CALL_BLOCK, CALL_ANCHOR, 'before')
    notes = (n_uni, n_func, n_call)
    if 'missing' in notes:
        return None, notes
    return text, notes


def inside_td():
    try:
        op  # noqa: F821
    except NameError:
        return False
    return True


def as_par(result):
    if isinstance(result, (list, tuple)):
        return result[0]
    return result


def td_op(*names):
    import builtins
    scopes = [globals()]
    if isinstance(__builtins__, dict):
        scopes.append(__builtins__)
    else:
        scopes.append(vars(builtins))
    for name in names:
        for scope in scopes:
            if name in scope:
                return scope[name]
    raise NameError('Operator type not found. Tried %s.' % (list(names),))


def place(node, x, y):
    node.nodeX = x
    node.nodeY = y
    return node


def music_page(rack):
    for existing in rack.customPages:
        if existing.name == 'Music':
            return existing
    return None


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


def input_path(node):
    try:
        links = list(node.inputConnectors[0].connections)
    except Exception:
        return '(unreadable)'
    if len(links) != 1 or links[0].owner is None:
        return '(none)' if not links else '(several)'
    return links[0].owner.path


def vec_rows(node):
    seq = None
    try:
        seq = node.seq.vec
    except Exception:
        seq = None
    count = 0
    if seq is not None:
        try:
            count = int(seq.numBlocks)
        except Exception:
            count = 0
    if count < 1:
        while hasattr(node.par, 'vec%dname' % count) and count < 32:
            count += 1
    rows = []
    for i in range(count):
        name_par = 'vec%dname' % i
        if not hasattr(node.par, name_par):
            break
        rows.append((i, str(getattr(node.par, name_par) or '')))
    return rows, seq


def bind_named(node, pairs):
    """Fill empty uniform slots. Refuses to rename a slot that already has another name."""
    rows, seq = vec_rows(node)
    have = {}
    for i, name in rows:
        if name and name not in have:
            have[name] = i
    missing = [name for name, _expr in pairs if name not in have]
    if missing and seq is not None:
        try:
            seq.numBlocks = len(rows) + len(missing)
        except Exception as err:
            print('fireworks: could not add uniform slots on %s: %s' % (node.path, err))
            return False, []
        rows, _seq = vec_rows(node)
        have = {}
        for i, name in rows:
            if name and name not in have:
                have[name] = i
    free = [i for i, name in rows if not name]
    fresh = []
    fi = 0
    ok = True
    for name, expr in pairs:
        if name in have:
            index = have[name]
            is_fresh = False
        elif fi < len(free):
            index = free[fi]
            fi += 1
            have[name] = index
            is_fresh = True
        else:
            print('fireworks: no free uniform slot for %s on %s' % (name, node.path))
            ok = False
            continue
        name_par = 'vec%dname' % index
        value_par = 'vec%dvaluex' % index
        if not hasattr(node.par, name_par) or not hasattr(node.par, value_par):
            print('fireworks: %s has no %s.' % (node.path, name_par))
            ok = False
            continue
        current = str(getattr(node.par, name_par) or '')
        if current not in ('', name):
            print('fireworks: refused to overwrite uniform %s on %s.' % (current, node.path))
            ok = False
            continue
        setattr(node.par, name_par, name)
        getattr(node.par, value_par).expr = expr
        if is_fresh:
            fresh.append(name)
            for suffix in ('valuey', 'valuez', 'valuew'):
                extra = 'vec%d%s' % (index, suffix)
                if hasattr(node.par, extra):
                    getattr(node.par, extra).val = 0
    return ok, fresh


def clear_uniforms(node, names):
    cleared = []
    for i, name in vec_rows(node)[0]:
        if name not in names:
            continue
        try:
            setattr(node.par, 'vec%dname' % i, '')
            value = getattr(node.par, 'vec%dvaluex' % i)
            value.expr = ''
            value.mode = ParMode.CONSTANT  # noqa: F821
            value.val = 0
            cleared.append(name)
        except Exception as err:
            print('fireworks: could not clear %s on %s: %s' % (name, node.path, err))
    return cleared


def ensure_toggle(page):
    owner = page.owner
    if hasattr(owner.par, 'Fireworks'):
        return owner.par.Fireworks, False
    par = as_par(page.appendToggle('Fireworks', label='Fireworks'))
    par.default = 0
    par.val = 0
    return par, True


def ensure_intensity(page):
    owner = page.owner
    if hasattr(owner.par, 'Fireworksintensity'):
        par = owner.par.Fireworksintensity
        created = False
    else:
        par = as_par(page.appendFloat('Fireworksintensity', label='Fireworks Intensity'))
        par.val = 1
        created = True
    par.default = 1
    par.normMin = 0
    par.normMax = 2
    par.min = 0
    par.max = 2
    par.clampMin = True
    par.clampMax = True
    return par, created


def destroy_par(rack, name):
    par = getattr(rack.par, name, None)
    if par is None:
        return False
    par.destroy()
    return True


def set_edge(node, value):
    for name in ('const0value', 'value0'):
        if hasattr(node.par, name):
            setattr(node.par, name, float(value))
            return True
    return False


def read_edge(node):
    for name in ('const0value', 'value0'):
        if hasattr(node.par, name):
            try:
                return float(getattr(node.par, name).eval())
            except Exception:
                return None
    return None


def name_edge(node):
    for name in ('const0name', 'name0'):
        if hasattr(node.par, name):
            current = str(getattr(node.par, name).eval() or '')
            if current in ('', 'chan1', 'constant0', 'const0'):
                setattr(node.par, name, 'edge')
            return True
    return False


def configure_callbacks(callbacks, rack):
    callbacks.text = EDGE_CALLBACKS
    try:
        callbacks.par.op = rack
    except Exception:
        callbacks.par.op = rack.path
    if hasattr(callbacks.par, 'pars'):
        callbacks.par.pars = 'Fireworks'
    if hasattr(callbacks.par, 'custom'):
        callbacks.par.custom = True
    if hasattr(callbacks.par, 'builtin'):
        callbacks.par.builtin = False
    if hasattr(callbacks.par, 'valuechange'):
        callbacks.par.valuechange = True
    if hasattr(callbacks.par, 'valueschanged'):
        callbacks.par.valueschanged = False
    callbacks.par.active = True


def cook_ms(node, repeats):
    import time
    node.cook(force=True)
    start = time.perf_counter()
    for _i in range(repeats):
        node.cook(force=True)
    return (time.perf_counter() - start) / float(repeats) * 1000.0


def measure(visual, rack, edge, callbacks):
    """Time visual with the fade forced off, then fully on. Restores the toggle."""
    repeats = 4
    prev_on = float(rack.par.Fireworks.eval())
    prev_gain = float(rack.par.Fireworksintensity.eval())
    prev_edge = read_edge(edge)
    was_active = True
    try:
        was_active = bool(callbacks.par.active.eval())
    except Exception:
        was_active = True
    callbacks.par.active = False
    try:
        rack.par.Fireworks = 0
        set_edge(edge, 0)
        try:
            edge.cook(force=True)
        except Exception:
            pass
        off_ms = cook_ms(visual, repeats)
        rack.par.Fireworks = 1
        if prev_gain <= 0.0:
            rack.par.Fireworksintensity = 1
        try:
            now = float(absTime.seconds)
        except Exception:
            now = 10.0
        set_edge(edge, max(0.001, now - 5.0))
        try:
            edge.cook(force=True)
        except Exception:
            pass
        on_ms = cook_ms(visual, repeats)
        return off_ms, on_ms, None
    except Exception as err:
        return None, None, str(err)
    finally:
        try:
            rack.par.Fireworks = prev_on
        except Exception as err:
            print('fireworks: could not restore the toggle: %s' % err)
        try:
            rack.par.Fireworksintensity = prev_gain
        except Exception as err:
            print('fireworks: could not restore the intensity: %s' % err)
        if prev_edge is None:
            set_edge(edge, 0 if prev_on < 0.5 else 0)
        else:
            set_edge(edge, prev_edge)
        try:
            edge.cook(force=True)
        except Exception:
            pass
        try:
            callbacks.par.active = was_active
        except Exception as err:
            print('fireworks: could not restore the toggle callback: %s' % err)


def apply_fireworks():
    rack = op(RACK)  # noqa: F821
    if rack is None:
        print('fireworks: %s is missing. Nothing was changed.' % RACK)
        return
    visual = rack.op('visual')
    shader = rack.op('visual_shader')
    preview = rack.op('preview')
    if visual is None or shader is None or preview is None:
        print('fireworks: need visual, visual_shader, and preview. Nothing was changed.')
        return
    try:
        bound = visual.par.pixeldat.eval()
    except Exception as err:
        print('fireworks: could not read the shader parameter: %s. Nothing was changed.' % err)
        return
    if dat_path(bound) != shader.path:
        print('fireworks: visual is not reading visual_shader. Nothing was changed.')
        print('fireworks: pixeldat is %s' % dat_path(bound))
        return
    if input_path(preview) != visual.path:
        print('fireworks: preview is not on visual. Nothing was changed.')
        print('fireworks: preview input is %s' % input_path(preview))
        return
    page = music_page(rack)
    if page is None:
        print('fireworks: the Music page is missing. Nothing was changed.')
        return

    before = norm(shader.text)
    patched, notes = patch_shader(before)
    if patched is None:
        print('fireworks: the picture shader does not have the expected sky anchors. Nothing was changed.')
        print('fireworks: notes %s' % (notes,))
        print('fireworks: uTitleStart present: %s' % (title_anchor(before) is not None))
        print('fireworks: terrain comment present: %s' % (before.count(CALL_ANCHOR) == 1))
        print('fireworks: void main present: %s' % (before.count(MAIN_ANCHOR) == 1))
        return

    before_errors = node_errors(visual)
    new_pars = []
    new_nodes = []
    fresh = []
    assigned = False

    def rollback(reason):
        if assigned:
            shader.text = before
            try:
                visual.cook(force=True)
            except Exception:
                pass
        if fresh:
            clear_uniforms(visual, fresh)
        for name in ('fireworks_callbacks', 'fireworks_edge'):
            if name not in new_nodes:
                continue
            node = rack.op(name)
            if node is None:
                continue
            try:
                node.destroy()
            except Exception as err:
                print('fireworks: could not remove %s: %s' % (name, err))
        for name in ('Fireworksintensity', 'Fireworks'):
            if name not in new_pars:
                continue
            try:
                destroy_par(rack, name)
            except Exception as err:
                print('fireworks: could not remove %s: %s' % (name, err))
        print('fireworks: %s' % reason)
        print('fireworks: the previous picture was put back.')

    try:
        _toggle, made_toggle = ensure_toggle(page)
        if made_toggle:
            new_pars.append('Fireworks')
        _gain, made_gain = ensure_intensity(page)
        if made_gain:
            new_pars.append('Fireworksintensity')
    except Exception as err:
        rollback('could not add the Music page controls: %s' % err)
        return

    try:
        edge = rack.op('fireworks_edge')
        if edge is None:
            edge = place(rack.create(td_op('constantCHOP'), 'fireworks_edge'), 980, 460)
            new_nodes.append('fireworks_edge')
            edge.color = (1.0, 0.45, 0.15)
            name_edge(edge)
            if not set_edge(edge, 0):
                raise RuntimeError('fireworks_edge has no value parameter')
        else:
            name_edge(edge)
        callbacks = rack.op('fireworks_callbacks')
        if callbacks is None:
            callbacks = place(
                rack.create(td_op('parameterexecuteDAT', 'parexecuteDAT', 'parexecDAT'), 'fireworks_callbacks'),
                700, 460)
            new_nodes.append('fireworks_callbacks')
            callbacks.color = (1.0, 0.45, 0.15)
        configure_callbacks(callbacks, rack)
        try:
            edge.cook(force=True)
        except Exception as err:
            print('fireworks: edge clock: %s' % err)
    except Exception as err:
        rollback('could not add the fade clock: %s' % err)
        return

    shader.text = patched
    assigned = True
    ok, fresh_now = bind_named(visual, UNIFORMS)
    fresh.extend(fresh_now)
    if not ok:
        rollback('the fireworks uniforms could not be bound.')
        return
    try:
        visual.cook(force=True)
    except Exception as err:
        rollback('visual cook failed: %s' % err)
        return
    problems = [item for item in node_errors(visual) if item not in before_errors]
    if problems:
        rollback('the shader failed to compile.')
        for item in problems:
            print('fireworks ERROR: %s' % item)
        return

    off_ms, on_ms, measure_err = measure(visual, rack, edge, callbacks)
    # One more cook so a mid-measure frame is not left on screen.
    try:
        visual.cook(force=True)
    except Exception:
        pass

    print('')
    print('visual.errors(): (none new)')
    print('Changed %s (%s).' % (shader.path, ', '.join(notes)))
    print('Music page: Fireworks toggle, Fireworks Intensity 0..2 default 1.')
    print('Fade %.2fs. While the fade is 0 the shell loop is not called.' % FADE_SECONDS)
    print('preview input left on %s.' % input_path(preview))
    if measure_err:
        print('fireworks: cook timing failed: %s' % measure_err)
        print('Turn Fireworks on and read the FPS number at the top of the TouchDesigner window.')
    else:
        added = on_ms - off_ms
        print('Forced cook of visual, fade 0: %.2f ms.' % off_ms)
        print('Forced cook of visual, fade 1 intensity 1: %.2f ms.' % on_ms)
        print('Fireworks added %.2f ms to that cook.' % added)
        if added >= 8.0:
            print('That is enough to pull the picture under 60 FPS while Fireworks is on.')
        else:
            print('That added time is small next to a 16.7 ms frame.')
        print('The FPS number at the top of the TouchDesigner window is the real frame rate.')
        print('Turn Fireworks on and read it.')
    print('The toggle was put back to the value it had before the timing cooks.')
    print('Ctrl+S keeps this in the .toe.')
    print('')


def load_builder_shader():
    src = open(BUILDER, encoding='utf-8').read()
    start_token = 'layout(location = 0) out vec4 fragColor;'
    end_token = 'fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));\n}'
    start = src.find(start_token)
    end = src.find(end_token, start)
    if start < 0 or end < 0:
        return None
    return src[start:end + len(end_token)]


def _balanced(text):
    return text.count('{') == text.count('}')


def self_check():
    shader = load_builder_shader()
    reasons = []
    if not shader or 'col += titleBanner' not in shader:
        reasons.append('builder shader')
        shader = shader or ''
    patched, notes = patch_shader(shader)
    again, notes2 = patch_shader(patched) if patched else (None, None)
    if patched is None or again != patched:
        reasons.append('idempotent %s %s' % (notes, notes2))
    else:
        call = patched.split(CALL_BEGIN, 1)[1].split(CALL_END, 1)[0]
        func = patched.split(FUNC_BEGIN, 1)[1].split(FUNC_END, 1)[0]
        if 'if (fireNow > 0.0 && uFireGain > 0.0)' not in call:
            reasons.append('early-out')
        guarded = call.split('if (fireNow', 1)[-1]
        if 'fireworksSky' not in guarded:
            reasons.append('call before check')
        if 'for (' in call:
            reasons.append('loop in call')
        if 'for (int i = 0; i < 7; i++)' not in func:
            reasons.append('shell loop')
        if patched.find(CALL_BEGIN) > patched.find('col += titleBanner'):
            reasons.append('title order')
        if patched.find(CALL_BEGIN) > patched.find('for (int k = 0; k < HIST; k++)'):
            reasons.append('terrain order')
        if not _balanced(patched):
            reasons.append('braces')
        if notes != ('inserted', 'inserted', 'inserted') or notes2 != ('updated', 'updated', 'updated'):
            reasons.append('notes %s %s' % (notes, notes2))
        if patched.count(CALL_ANCHOR) != 1 or patched.count('void main()') != 1:
            reasons.append('anchors duplicated')
    undo_ns = {'FIREWORKS_UNDO_NO_RUN': True}
    exec(open(UNDO_PATH, encoding='utf-8').read(), undo_ns)
    cleaned = undo_ns['strip_shader'](patched) if patched else None
    if cleaned is None or 'FIREWORKS_' in cleaned or 'uFireOn' in cleaned or 'fireworksSky' in cleaned:
        reasons.append('strip')
    elif 'col += titleBanner' not in cleaned or cleaned.count(CALL_ANCHOR) != 1:
        reasons.append('strip damaged terrain')
    reapplied, _notes3 = patch_shader(cleaned) if cleaned else (None, None)
    if reapplied != patched:
        reasons.append('reapply')
    crown_ns = {'CROWN_SHAPE_NO_RUN': True}
    exec(open(CROWN_PATH, encoding='utf-8').read(), crown_ns)
    crowned, _crown_notes = crown_ns['patch_shader'](shader)
    fired, fire_notes = patch_shader(crowned) if crowned else (None, None)
    if fired is None or 'missing' in fire_notes:
        reasons.append('crown+fire %s' % (fire_notes,))
    else:
        bare = undo_ns['strip_shader'](fired)
        if bare != crowned or 'crownOffset' not in (bare or '') or 'FIREWORKS_' in (bare or ''):
            reasons.append('strip keeps crown')
        if fired.count('float yl = base + crownOffset') < 1:
            reasons.append('crown line')
    me = open(SETUP_PATH, encoding='utf-8').read()
    if "appendFloat('Fireworksintensity'" not in me or 'parent().par.Fireworksintensity' not in me:
        reasons.append('intensity')
    if SHELLS != 7:
        reasons.append('shell constant')
    ok = not reasons
    print('fireworks self-check: %s' % ('ok' if ok else 'FAILED'))
    if reasons:
        print('fireworks self-check: %s' % ', '.join(reasons))
    return ok


if globals().get('FIREWORKS_NO_RUN'):
    pass
elif inside_td():
    apply_fireworks()
else:
    print('Open C:\\Users\\James\\Desktop\\TOUCH\\NewProject.8.toe, then run this in the Textport:')
    print("  exec(open(r'C:\\Users\\James\\Desktop\\TOUCH\\fireworks_setup.py', encoding='utf-8').read())")
    self_check()
