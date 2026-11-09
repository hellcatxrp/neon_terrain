# Fast look at the crown wiring. Does not download full frames.
# Read-only: creates nothing and changes nothing.
#
# 2026-11-10: adds errors(recurse=True) for crown_vis and every child, the real
#   sizes of crown_movie/crown_key/crown_stack/title_card, the corner colour the
#   Movie File In delivers, the key uniforms, visual's uGif* layout uniforms,
#   the Asset menu, and title_card/crown_stack alpha where no glyph is
#   (above 0 there means the title crosses the sky as a solid rectangle).
#
# Textport, after the slow probe has finished:
#   exec(open(r'C:\Users\James\Desktop\TOUCH\probe_crown.py', encoding='utf-8').read())

RACK = '/project1/music_rack'


def inside_td():
    try:
        op  # noqa: F821
    except NameError:
        return False
    return True


def inp(node, index):
    if node is None:
        return '(missing node)'
    try:
        src = node.inputs[index]
    except Exception as err:
        return 'unreadable (%s)' % err
    if src is None:
        return '(none)'
    return src.path


def errs(node):
    if node is None:
        return []
    try:
        found = node.errors(recurse=False)
    except TypeError:
        found = node.errors()
    except Exception as err:
        return ['errors() failed: %s' % err]
    if isinstance(found, str):
        # TouchDesigner returns one string. Iterating it would print single letters.
        return [found] if found.strip() else []
    return [str(item) for item in (found or [])]


def info_lines(node):
    lines = []
    try:
        docked = list(node.docked)
    except Exception:
        return lines
    for extra in docked:
        if extra is None or 'info' not in (extra.name or '').lower():
            continue
        try:
            text = extra.text
        except Exception:
            continue
        for line in text.splitlines():
            low = line.lower()
            if 'error' in low or 'warning' in low:
                lines.append(line.strip()[:220])
    return lines[:8]


def peek(node):
    if node is None:
        print('  (missing)')
        return
    print(node.path, node.OPType)
    found = errs(node)
    print('  errors:', found or '(none)')
    for line in info_lines(node):
        print('  info:', line)
    if getattr(node, 'family', '') != 'TOP':
        return
    try:
        color = node.sample(u=0.5, v=0.2)
        print('  centre-low sample %.3f %.3f %.3f  alpha %.3f' % (
            float(color[0]), float(color[1]), float(color[2]), float(color[3])))
        print('  size %sx%s' % (node.width, node.height))
    except Exception as err:
        print('  sample failed:', err)


def probe():
    rack = op(RACK)
    if rack is None:
        print('probe: %s is missing.' % RACK)
        return
    visual = rack.op('visual')
    preview = rack.op('preview')
    shader = rack.op('visual_shader')
    print('preview input:', inp(preview, 0))
    print('visual input 0:', inp(visual, 0))
    print('visual input 1:', inp(visual, 1))
    print('visual input 2:', inp(visual, 2))
    print('visual errors:', errs(visual) or '(none)')
    print('preview errors:', errs(preview) or '(none)')
    body = shader.text if shader is not None else ''
    for token in ('REST_LIFT', 'crownOffset', 'GIF_UNDER begin', 'GIF_TITLE begin'):
        print('shader %-16s %s' % (token, body.count(token)))
    for line in body.splitlines():
        if 'const float REST_LIFT' in line or 'const float CROWN_SCALE' in line:
            print(' ', line.strip())
    base = rack.op('crown_vis')
    print('crown_vis:', base.path if base else '(missing)')
    if base is not None:
        for name in (
            'crown_movie', 'crown_key', 'crown_stack',
            'gif_movie', 'gif_key', 'gif_stack', 'crown_over',
        ):
            node = base.op(name)
            if node is None:
                continue
            peek(node)
    for name in ('crown_movie', 'crown_frame', 'crown_over'):
        node = rack.op(name)
        if node is None:
            continue
        print('rack leftover', node.path, node.OPType, errs(node) or '(no errors)')
    deep(rack, base, visual)
    print('probe done')


def rgba(node, u, v):
    try:
        c = node.sample(u=u, v=v)
        return '%.3f %.3f %.3f a%.3f' % (float(c[0]), float(c[1]), float(c[2]), float(c[3]))
    except Exception as err:
        return 'sample failed (%s)' % err


def par_text(node, name):
    par = getattr(node.par, name, None) if node is not None else None
    if par is None:
        return '(no %s)' % name
    try:
        expr = par.expr if par.mode == ParMode.EXPRESSION else ''  # noqa: F821
    except Exception:
        expr = ''
    try:
        value = par.eval()
    except Exception as err:
        value = 'eval failed (%s)' % err
    return '%s=%s%s' % (name, value, ('  expr %s' % expr) if expr else '')


def uniforms(node):
    found = []
    i = 0
    while node is not None and hasattr(node.par, 'vec%dname' % i) and i < 64:
        name = str(getattr(node.par, 'vec%dname' % i) or '')
        if name:
            found.append('%s=%s' % (name, par_text(node, 'vec%dvaluex' % i).split('=', 1)[1]))
        i += 1
    return found


def deep(rack, base, visual):
    print('')
    print('--- red X: errors anywhere inside crown_vis')
    if base is None:
        print('crown_vis missing')
    else:
        try:
            print('crown_vis.errors(recurse=True):', base.errors(recurse=True) or '(none)')
        except Exception as err:
            print('crown_vis.errors(recurse=True) failed:', err)
        for child in base.children:
            found = errs(child)
            dock = getattr(child, 'dock', None)
            print('  %-22s %-14s %s%s' % (
                child.name, child.OPType, ' '.join(found) or 'ok',
                ('  (docked to %s)' % dock.name) if dock is not None else ''))
    print('')
    print('--- sizes and parameters')
    title = rack.op('title_card')
    movie = base.op('crown_movie') if base is not None else None
    key = base.op('crown_key') if base is not None else None
    stack = base.op('crown_stack') if base is not None else None
    for node in (movie, key, stack, base.op('crown_title_in') if base is not None else None, title, visual):
        if node is None:
            continue
        try:
            size = '%sx%s' % (node.width, node.height)
        except Exception:
            size = '?'
        print('%-34s %-10s %s %s' % (node.path, size, par_text(node, 'format'), par_text(node, 'inputfiltertype')))
    if movie is not None:
        print('crown_movie', par_text(movie, 'file'))
        for name in ('inputcolorspace', 'premultrgbbyalpha', 'decodepixelformat', 'playmode'):
            if hasattr(movie.par, name):
                print('crown_movie', par_text(movie, name))
        print('')
        print('--- colour the key actually sees (0-1). In the file the backdrop is about 0.148 0.153 0.004')
        for label, u, v in (('bottom-left', 0.01, 0.01), ('bottom-right', 0.99, 0.01),
                            ('top-left', 0.01, 0.99), ('top-right', 0.99, 0.99), ('centre', 0.5, 0.5)):
            print('  crown_movie %-12s %s' % (label, rgba(movie, u, v)))
    if key is not None:
        print('crown_key uniforms:', uniforms(key))
        print('crown_key', par_text(key, 'resolutionw'), par_text(key, 'resolutionh'))
    if stack is not None:
        print('crown_stack', par_text(stack, 'resolutionw'))
        print('crown_stack', par_text(stack, 'resolutionh'))
    if base is not None:
        for name in ('Gifscale', 'Gifx', 'Gify'):
            print('crown_vis', par_text(base, name))
    print('visual uniforms:', uniforms(visual))
    for name in ('Asset', 'Assetkey', 'Titleanim'):
        print('music_rack', par_text(rack, name))
    print('')
    print('--- white rectangle: alpha where the title card has no glyphs (should be 0)')
    if title is not None:
        print('title_card', par_text(title, 'bgalpha'), par_text(title, 'fontalpha'), par_text(title, 'text'))
        for label, u, v in (('margin bottom-left', 0.01, 0.01), ('margin top-right', 0.99, 0.99)):
            print('  title_card %-20s %s' % (label, rgba(title, u, v)))
    if stack is not None and title is not None:
        try:
            sw, sh = float(stack.width), float(stack.height)
            th = float(title.height)
            tw = float(title.width)
            for label, x, y in (('title rows, left margin', 2.0, sh - th + 2.0),
                                ('title rows, top right', min(tw, sw) - 2.0, sh - 2.0),
                                ('right of the card', min(sw - 2.0, tw + 4.0), sh - 2.0)):
                print('  crown_stack %-24s %s' % (label, rgba(stack, x / sw, y / sh)))
        except Exception as err:
            print('  crown_stack title rows:', err)
    print('If those alphas are above 0, the title flies as a rectangle. add_gif.py sets')
    print("title_card bgalpha to 0 when its margin is not clear, and prints what it found.")


if inside_td():
    probe()
else:
    print('Run this inside the TouchDesigner textport:')
    print("  exec(open(r'C:\\Users\\James\\Desktop\\TOUCH\\probe_crown.py', encoding='utf-8').read())")
