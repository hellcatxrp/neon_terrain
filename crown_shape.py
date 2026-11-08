# Crown resting shape for every row in visual_shader.
# Does not create operators, does not move preview, and does not change audio wiring.
#
# Textport:
#   exec(open(r'C:\Users\James\Desktop\TOUCH\crown_shape.py', encoding='utf-8').read())
#
# Revert (puts the original picture text back):
#   exec(open(r'C:\Users\James\Desktop\TOUCH\restore_picture.py', encoding='utf-8').read())

RACK = '/project1/music_rack'

YL = (
    '        float yl = base + ridge(k, wx - dx * scale) * hs;\n'
    '        float y0 = base + ridge(k, wx) * hs;\n'
    '        float yr = base + ridge(k, wx + dx * scale) * hs;\n'
)
PX_LINE = 'const float PX = 1.0 / 720.0;\n'
MAIN = 'void main()\n'

CONST_BEGIN = '// CROWN_SHAPE const begin'
CONST_END = '// CROWN_SHAPE const end'
FUNC_BEGIN = '// CROWN_SHAPE begin'
FUNC_END = '// CROWN_SHAPE end'
Y_BEGIN = '        // CROWN_Y begin'
Y_END = '// CROWN_Y end'

# CROWN_SCALE 0.10 is the centre spike at the front row.
# REST_LIFT raises every row through the same /z as the audio.
# At the front, valleys land near y=0.32 and the centre near y=0.39.
# REACT_GAIN and REACT_BASE are 0, so ridge * hs is unchanged.
CONST_BLOCK = '''// CROWN_SHAPE const begin
const float CROWN_SCALE = 0.10;
const float REST_LIFT = 0.20;
const float REACT_GAIN = 0.0;
const float REACT_BASE = 0.0;
// CROWN_SHAPE const end
'''

FUNC_BLOCK = '''// CROWN_SHAPE begin
// Normalised x across the frame. Five spikes, centre tallest, linear between points.
float crown(float x)
{
    float u = clamp(x, 0.0, 1.0);
    if (u < 0.10) return mix(0.20, 0.60, (u - 0.00) / 0.10);
    if (u < 0.20) return mix(0.60, 0.25, (u - 0.10) / 0.10);
    if (u < 0.30) return mix(0.25, 0.80, (u - 0.20) / 0.10);
    if (u < 0.40) return mix(0.80, 0.25, (u - 0.30) / 0.10);
    if (u < 0.50) return mix(0.25, 1.00, (u - 0.40) / 0.10);
    if (u < 0.60) return mix(1.00, 0.25, (u - 0.50) / 0.10);
    if (u < 0.70) return mix(0.25, 0.80, (u - 0.60) / 0.10);
    if (u < 0.80) return mix(0.80, 0.25, (u - 0.70) / 0.10);
    if (u < 0.90) return mix(0.25, 0.60, (u - 0.80) / 0.10);
    return mix(0.60, 0.20, (u - 0.90) / 0.10);
}

// Same 1/z perspective as hs = HEIGHT / z. Added on every row.
float crownOffset(float x, float z, float audio)
{
    float c = crown(x);
    return (REST_LIFT + c * CROWN_SCALE * (1.0 + audio * REACT_GAIN) + audio * REACT_BASE) / z;
}
// CROWN_SHAPE end
'''

Y_BLOCK = '''        // CROWN_Y begin
        float xL = (p.x - dx) / 1.7778 + 0.5;
        float x0 = p.x / 1.7778 + 0.5;
        float xR = (p.x + dx) / 1.7778 + 0.5;
        float al = ridge(k, wx - dx * scale);
        float a0 = ridge(k, wx);
        float ar = ridge(k, wx + dx * scale);
        float yl = base + crownOffset(xL, z, al) + al * hs;
        float y0 = base + crownOffset(x0, z, a0) + a0 * hs;
        float yr = base + crownOffset(xR, z, ar) + ar * hs;
        // CROWN_Y end
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


def apply_block(text, begin, end, block, anchor, inserted):
    found = replace_span(text, begin, end, block)
    if found is not None:
        return found, 'updated'
    if text.count(anchor) != 1:
        return text, 'missing'
    return text.replace(anchor, inserted, 1), 'inserted'


def patch_shader(text):
    text = norm(text)
    text, n_const = apply_block(
        text, CONST_BEGIN, CONST_END, CONST_BLOCK, PX_LINE, PX_LINE + CONST_BLOCK)
    text, n_func = apply_block(
        text, FUNC_BEGIN, FUNC_END, FUNC_BLOCK, MAIN, FUNC_BLOCK + MAIN)
    text, n_y = apply_block(
        text, Y_BEGIN, Y_END, Y_BLOCK, YL, Y_BLOCK)
    notes = (n_const, n_func, n_y)
    if 'missing' in notes:
        return None, notes
    return text, notes


def inside_td():
    try:
        op  # noqa: F821
    except NameError:
        return False
    return True


def dat_path(value):
    path = getattr(value, 'path', None)
    if path:
        return path
    return str(value or '')


def node_errors(node):
    try:
        return [str(item) for item in (node.errors() or [])]
    except Exception:
        return []


def input_path(node):
    try:
        links = list(node.inputConnectors[0].connections)
    except Exception:
        return '(unreadable)'
    if len(links) != 1 or links[0].owner is None:
        return '(none)' if not links else '(several)'
    return links[0].owner.path


def apply_shape():
    rack = op(RACK)
    if rack is None:
        print('crown shape: %s is missing. Nothing was changed.' % RACK)
        return
    visual = rack.op('visual')
    shader = rack.op('visual_shader')
    preview = rack.op('preview')
    if visual is None or shader is None:
        print('crown shape: visual or visual_shader is missing. Nothing was changed.')
        return

    try:
        bound = visual.par.pixeldat.eval()
    except Exception as err:
        bound = None
        print('crown shape: could not read the shader parameter: %s' % err)
    if dat_path(bound) != shader.path:
        print('crown shape: visual is not reading visual_shader. Nothing was changed.')
        print('crown shape: pixeldat is %s' % dat_path(bound))
        return

    before = norm(shader.text)
    patched, notes = patch_shader(before)
    if patched is None:
        print('crown shape: the height lines are not the original terrain lines. Nothing was changed.')
        print('crown shape: original Y line present: %s' % (YL in before))
        return
    if patched == before:
        print('crown shape: already applied. No operators were changed.')
        return

    shader.text = patched
    problems = []
    try:
        visual.cook(force=True)
    except Exception as err:
        problems.append('visual cook: %s' % err)
    problems.extend(node_errors(visual))
    if problems:
        shader.text = before
        try:
            visual.cook(force=True)
        except Exception:
            pass
        print('crown shape: the shader failed to compile. The previous text was put back.')
        for item in problems:
            print('crown shape ERROR: %s' % item)
        return

    print('')
    print('visual.errors(): (none)')
    print('Changed %s only (%s).' % (shader.path, ', '.join(notes)))
    print('Every row rests on the crown. Audio is still ridge * hs.')
    print('CROWN_SCALE 0.10, REST_LIFT 0.20, REACT_GAIN 0, REACT_BASE 0.')
    if preview is not None:
        print('preview input left on %s.' % input_path(preview))
    print('No operators were created or rewired.')
    print('')


def self_check():
    src = open(r'C:\Users\James\Desktop\TOUCH\build_music_rack.py', encoding='utf-8').read()
    if src.count(YL) != 1:
        print('crown shape self-check: FAILED, Y count %s' % src.count(YL))
        return False
    patched, notes = patch_shader(src)
    again, notes2 = patch_shader(patched) if patched else (None, None)
    ok = (
        patched is not None
        and again == patched
        and patched.count(YL) == 0
        and patched.count('CROWN_SCALE') >= 1
        and 'float yl = base + crownOffset(xL, z, al) + al * hs;' in patched
        and 'k == 0) ? crown' not in patched
        and 'const float CROWN_SCALE = 0.10;' in patched
        and 'return pow(clamp(v, 0.0, 1.0), 1.35)' in patched
        and notes == ('inserted', 'inserted', 'inserted')
        and notes2 == ('updated', 'updated', 'updated')
    )
    print('crown shape self-check: %s' % ('ok' if ok else 'FAILED'))
    return ok


if not globals().get('CROWN_SHAPE_NO_RUN'):
    if inside_td():
        apply_shape()
    else:
        print('Run this inside the TouchDesigner textport:')
        print("  exec(open(r'C:\\Users\\James\\Desktop\\TOUCH\\crown_shape.py', encoding='utf-8').read())")
        self_check()
