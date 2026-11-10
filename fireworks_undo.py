# Remove the fireworks show from /project1/music_rack.
# Deletes the marked shader blocks, the Fireworks toggle, Fireworks Intensity,
# the fade clock, and the three uniforms. Leaves preview, audio, and the title.
#
# Open the same .toe the setup edited (NewProject.8.toe), then the Textport:
#   exec(open(r'C:\Users\James\Desktop\TOUCH\fireworks_undo.py', encoding='utf-8').read())

RACK = '/project1/music_rack'
SETUP_PATH = r'C:\Users\James\Desktop\TOUCH\fireworks_setup.py'
BUILDER = r'C:\Users\James\Desktop\TOUCH\build_music_rack.py'

UNI_BEGIN = '// FIREWORKS_UNIFORMS begin'
UNI_END = '// FIREWORKS_UNIFORMS end'
FUNC_BEGIN = '// FIREWORKS_FUNC begin'
FUNC_END = '// FIREWORKS_FUNC end'
CALL_BEGIN = '    // FIREWORKS_CALL begin'
CALL_END = '    // FIREWORKS_CALL end'

UNIFORM_NAMES = ('uFireOn', 'uFireEdge', 'uFireGain')
PAR_NAMES = ('Fireworksintensity', 'Fireworks')
NODE_NAMES = ('fireworks_callbacks', 'fireworks_edge')


def norm(text):
    return (text or '').replace('\r\n', '\n').replace('\r', '\n')


def remove_span(text, begin, end):
    b = text.find(begin)
    if b < 0 or text.find(end, b + len(begin)) < 0:
        return None
    e = text.find(end, b + len(begin)) + len(end)
    if e < len(text) and text[e] == '\n':
        e += 1
    return text[:b] + text[e:]


def strip_shader(text):
    """Drop the three marked blocks. None means a block is half-present."""
    text = norm(text)
    pairs = (
        (UNI_BEGIN, UNI_END),
        (FUNC_BEGIN, FUNC_END),
        (CALL_BEGIN, CALL_END),
    )
    for begin, end in pairs:
        if begin not in text and end not in text:
            continue
        found = remove_span(text, begin, end)
        if found is None:
            return None
        text = found
    leftover = ('FIREWORKS_', 'uFireOn', 'uFireEdge', 'uFireGain', 'fireworksSky', 'fireFade(')
    for token in leftover:
        if token in text:
            return None
    return text


def inside_td():
    try:
        op  # noqa: F821
    except NameError:
        return False
    return True


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
    return rows


def clear_uniforms(node):
    cleared = []
    for i, name in vec_rows(node):
        if name not in UNIFORM_NAMES:
            continue
        try:
            setattr(node.par, 'vec%dname' % i, '')
            value = getattr(node.par, 'vec%dvaluex' % i)
            value.expr = ''
            value.mode = ParMode.CONSTANT  # noqa: F821
            value.val = 0
            cleared.append(name)
        except Exception as err:
            print('fireworks undo: could not clear %s: %s' % (name, err))
    return cleared


def destroy_par(rack, name):
    par = getattr(rack.par, name, None)
    if par is None:
        return None
    par.destroy()
    return name


def remove_fireworks():
    rack = op(RACK)  # noqa: F821
    if rack is None:
        print('fireworks undo: %s is missing. Nothing was changed.' % RACK)
        return
    visual = rack.op('visual')
    shader = rack.op('visual_shader')
    preview = rack.op('preview')
    if visual is None or shader is None:
        print('fireworks undo: visual or visual_shader is missing. Nothing was changed.')
        return
    try:
        bound = visual.par.pixeldat.eval()
    except Exception as err:
        print('fireworks undo: could not read the shader parameter: %s. Nothing was changed.' % err)
        return
    if dat_path(bound) != shader.path:
        print('fireworks undo: visual is not reading visual_shader. Nothing was changed.')
        print('fireworks undo: pixeldat is %s' % dat_path(bound))
        return

    before = norm(shader.text)
    stripped = strip_shader(before)
    if stripped is None:
        print('fireworks undo: a fireworks block is incomplete. Nothing was changed.')
        return
    had_block = stripped != before
    had_nodes = any(rack.op(name) is not None for name in NODE_NAMES)
    had_pars = any(getattr(rack.par, name, None) is not None for name in PAR_NAMES)
    had_uniforms = any(name in UNIFORM_NAMES for _i, name in vec_rows(visual))
    if not had_block and not had_nodes and not had_pars and not had_uniforms:
        print('fireworks undo: nothing to remove.')
        if preview is not None:
            print('preview input left on %s.' % input_path(preview))
        return

    before_errors = node_errors(visual)
    if had_block:
        shader.text = stripped
        try:
            visual.cook(force=True)
        except Exception as err:
            shader.text = before
            try:
                visual.cook(force=True)
            except Exception:
                pass
            print('fireworks undo: visual cook failed. The shader text was put back.')
            print('fireworks undo: %s' % err)
            return
        problems = [item for item in node_errors(visual) if item not in before_errors]
        if problems:
            shader.text = before
            try:
                visual.cook(force=True)
            except Exception:
                pass
            print('fireworks undo: the shader failed to compile. The previous text was put back.')
            for item in problems:
                print('fireworks undo ERROR: %s' % item)
            return

    # Callbacks first, so deleting the toggle does not write the clock.
    removed_nodes = []
    for name in NODE_NAMES:
        node = rack.op(name)
        if node is None:
            continue
        try:
            if hasattr(node.par, 'active'):
                node.par.active = False
        except Exception:
            pass
        try:
            path = node.path
            node.destroy()
            removed_nodes.append(path)
        except Exception as err:
            print('fireworks undo: could not delete %s: %s' % (node.path, err))

    cleared = clear_uniforms(visual)
    removed_pars = []
    for name in PAR_NAMES:
        try:
            gone = destroy_par(rack, name)
        except Exception as err:
            print('fireworks undo: could not remove %s: %s' % (name, err))
            gone = None
        if gone:
            removed_pars.append(gone)

    print('')
    print('Removed shader blocks: %s' % ('yes' if had_block else 'no'))
    print('Removed parameters: %s' % (', '.join(removed_pars) or '(none)'))
    print('Removed nodes: %s' % (', '.join(removed_nodes) or '(none)'))
    print('Cleared uniforms: %s' % (', '.join(cleared) or '(none)'))
    if preview is not None:
        print('preview input left on %s.' % input_path(preview))
    print('Ctrl+S keeps this in the .toe.')
    print('')


def self_check():
    ns = {'FIREWORKS_NO_RUN': True}
    exec(open(SETUP_PATH, encoding='utf-8').read(), ns)
    src = open(BUILDER, encoding='utf-8').read()
    start = src.find('layout(location = 0) out vec4 fragColor;')
    end_token = 'fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));\n}'
    end = src.find(end_token, start)
    shader = src[start:end + len(end_token)]
    patched, notes = ns['patch_shader'](shader)
    cleaned = strip_shader(patched) if patched else None
    reasons = []
    if patched is None:
        reasons.append('patch %s' % (notes,))
    if cleaned is None:
        reasons.append('strip')
    elif cleaned != shader and 'FIREWORKS_' not in shader:
        # The insert keeps the original anchors, so a round trip matches.
        if 'col += titleBanner' not in cleaned or 'uFireOn' in cleaned:
            reasons.append('round trip')
        if cleaned.count('void main()') != shader.count('void main()'):
            reasons.append('main count')
    if cleaned is not None and cleaned != shader:
        reasons.append('text differs')
    me = open(SETUP_PATH, encoding='utf-8').read()
    undo = open(__file__, encoding='utf-8').read() if '__file__' in globals() else open(
        r'C:\Users\James\Desktop\TOUCH\fireworks_undo.py', encoding='utf-8').read()
    for token in (UNI_BEGIN, FUNC_BEGIN, CALL_BEGIN):
        if token not in me or token not in undo:
            reasons.append('marker %s' % token)
    ok = not reasons
    print('fireworks undo self-check: %s' % ('ok' if ok else 'FAILED'))
    if reasons:
        print('fireworks undo self-check: %s' % ', '.join(reasons))
    return ok


if globals().get('FIREWORKS_UNDO_NO_RUN'):
    pass
elif inside_td():
    remove_fireworks()
else:
    print('Open C:\\Users\\James\\Desktop\\TOUCH\\NewProject.8.toe, then run this in the Textport:')
    print("  exec(open(r'C:\\Users\\James\\Desktop\\TOUCH\\fireworks_undo.py', encoding='utf-8').read())")
    self_check()
