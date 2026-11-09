# Put the neon line back on /project1/music_rack/preview.
# Writes the original shader text into the existing visual_shader DAT and
# points preview at visual again. Does not rebuild the rack and does not
# delete crown_vis.
#
# 2026-11-10: also removes the Asset, Asset Key, and Reload Assets parameters
#   from the Music page, deletes crown_vis/asset_callbacks and asset_table, and
#   blanks the uGif* layout uniforms add_gif.py put on visual.
#
# Textport:
#   exec(open(r'C:\Users\James\Desktop\TOUCH\restore_picture.py', encoding='utf-8').read())

RACK = '/project1/music_rack'
BUILDER = r'C:\Users\James\Desktop\TOUCH\build_music_rack.py'
ASSET_PARS = ('Asset', 'Assetkey', 'Reloadassets')
ASSET_NODES = ('asset_callbacks', 'asset_table')

UNIFORMS = (
    ('uTime', "op('vis_features')['time']"),
    ('uPunch', 'parent().par.Punch'),
    ('uClock', 'absTime.seconds'),
    ('uTitleStart', "op('title_flight')[0]"),
)


def load_original_shader():
    src = open(BUILDER, encoding='utf-8').read()
    start_token = 'layout(location = 0) out vec4 fragColor;'
    end_token = 'fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));\n}'
    start = src.find(start_token)
    end = src.find(end_token, start)
    if start < 0 or end < 0:
        return None
    end += len(end_token)
    shader = src[start:end]
    if shader.count(start_token) != 1 or 'float yl = base + ridge' not in shader:
        return None
    if 'CROWN_PROFILE' in shader:
        return None
    return shader


def inside_td():
    try:
        op  # noqa: F821
    except NameError:
        return False
    return True


def input_path(node):
    try:
        links = list(node.inputConnectors[0].connections)
    except Exception:
        return '(unreadable)'
    if len(links) != 1 or links[0].owner is None:
        return '(none)' if not links else '(several)'
    return links[0].owner.path


def vec_slots(node):
    count = 0
    try:
        count = int(node.seq.vec.numBlocks)
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


def restore_uniforms(visual):
    rows = vec_slots(visual)
    try:
        seq = visual.seq.vec
    except Exception:
        seq = None
    have = {}
    for index, name in rows:
        if name and name not in have:
            have[name] = index
    missing = [name for name, _expr in UNIFORMS if name not in have]
    if missing and seq is not None:
        try:
            if int(seq.numBlocks) < len(UNIFORMS):
                seq.numBlocks = len(UNIFORMS)
        except Exception as err:
            print('restore: uniform slots: %s' % err)
        rows = vec_slots(visual)
        have = {}
        for index, name in rows:
            if name and name not in have:
                have[name] = index
    used = set(have.values())
    free = [
        index for index, name in rows
        if index not in used and (
            not name or name.startswith('uCrown') or name.startswith('uGif')
            or name.startswith('uReact'))
    ]
    fi = 0
    ok = True
    for name, expr in UNIFORMS:
        if name in have:
            index = have[name]
        elif fi < len(free):
            index = free[fi]
            fi += 1
            have[name] = index
        else:
            print('restore: no slot for %s' % name)
            ok = False
            continue
        name_par = 'vec%dname' % index
        value_par = 'vec%dvaluex' % index
        if not hasattr(visual.par, name_par) or not hasattr(visual.par, value_par):
            print('restore: missing %s' % name_par)
            ok = False
            continue
        previous = str(getattr(visual.par, name_par) or '')
        setattr(visual.par, name_par, name)
        getattr(visual.par, value_par).expr = expr
        print('restore: %s %s (was %s)' % (name_par, name, previous or 'blank'))
    return ok


def clear_gif_uniforms(visual):
    """Blank uGif* slots. The original shader has no such uniforms, and their
    expressions point into crown_vis."""
    cleared = []
    for index, name in vec_slots(visual):
        if not name.startswith('uGif'):
            continue
        try:
            setattr(visual.par, 'vec%dname' % index, '')
            value = getattr(visual.par, 'vec%dvaluex' % index)
            value.expr = ''
            value.mode = ParMode.CONSTANT  # noqa: F821
            value.val = 0
            cleared.append(name)
        except Exception as err:
            print('restore: could not clear %s: %s' % (name, err))
    return cleared


def remove_asset_menu(rack):
    """Callbacks first, so removing the parameters triggers nothing."""
    removed = []
    base = rack.op('crown_vis')
    for name in ASSET_NODES:
        node = base.op(name) if base is not None else None
        if node is None:
            continue
        try:
            node.destroy()
            removed.append('crown_vis/' + name)
        except Exception as err:
            print('restore: could not delete %s: %s' % (node.path, err))
    for name in ASSET_PARS:
        par = getattr(rack.par, name, None)
        if par is None:
            continue
        try:
            par.destroy()
            removed.append('par ' + name)
        except Exception as err:
            print('restore: could not remove parameter %s: %s' % (name, err))
    return removed


def restore_title_input(visual, rack):
    """Point visual input 2 back at title_card when the gif stack is on it."""
    title = rack.op('title_card')
    if visual is None or title is None:
        return 'skipped'
    try:
        connectors = list(visual.inputConnectors)
    except Exception as err:
        return 'unreadable: %s' % err
    if len(connectors) < 3:
        return 'no input 2'
    links = list(connectors[2].connections)
    owner = links[0].owner if len(links) == 1 else None
    if owner is not None and owner.path == title.path:
        return title.path
    if owner is not None and owner.name not in ('crown_stack', 'gif_stack', 'crown_vis'):
        return 'left on %s' % owner.path
    try:
        connectors[2].connect(title)
    except Exception as err:
        return 'failed: %s' % err
    return title.path


def restore():
    shader_text = load_original_shader()
    if shader_text is None:
        print('restore: could not read the original shader from build_music_rack.py. Nothing was changed.')
        return

    rack = op(RACK)
    if rack is None:
        print('restore: %s is missing. Nothing was changed.' % RACK)
        return
    visual = rack.op('visual')
    shader = rack.op('visual_shader')
    preview = rack.op('preview')
    if visual is None or shader is None or preview is None:
        print('restore: need visual, visual_shader, and preview. Nothing was changed.')
        print('restore: children: %s' % [c.name for c in rack.children])
        return

    before_input = input_path(preview)
    shader.text = shader_text
    try:
        visual.par.pixeldat = shader
    except Exception as err:
        print('restore: pixeldat: %s' % err)
    restore_uniforms(visual)
    cleared = clear_gif_uniforms(visual)
    input2 = restore_title_input(visual, rack)
    asset_removed = remove_asset_menu(rack)

    wired = False
    try:
        preview.inputConnectors[0].connect(visual)
        wired = True
    except Exception as err:
        print('restore: could not connect preview to visual: %s' % err)

    problems = []
    for node in (visual, preview):
        try:
            node.cook(force=True)
        except Exception as err:
            problems.append('%s cook: %s' % (node.path, err))
        try:
            for item in node.errors() or []:
                problems.append('%s: %s' % (node.path, item))
        except Exception:
            pass

    print('')
    print('preview input was %s' % before_input)
    print('preview input is %s' % input_path(preview))
    print('visual input 2 is %s' % input2)
    print('visual_shader now holds the original terrain text (%s chars).' % len(shader.text))
    print('cleared uniforms on visual: %s' % (', '.join(cleared) or '(none)'))
    print('removed asset menu: %s' % (', '.join(asset_removed) or '(nothing to remove)'))
    try:
        print('visual resolution %sx%s' % (visual.width, visual.height))
    except Exception:
        pass
    for item in problems:
        print('restore ERROR: %s' % item)
    if wired and not problems:
        print('The neon line should be back on the preview window.')
    print('crown_vis was left in the network and is not on screen.')
    print('')


def self_check():
    shader = load_original_shader()
    ok = (
        shader is not None
        and 'float yl = base + ridge(k, wx - dx * scale) * hs;' in shader
        and 'CROWN_' not in shader
        and shader.strip().endswith('}')
    )
    print('restore self-check: %s (%s chars)' % ('ok' if ok else 'FAILED', 0 if shader is None else len(shader)))
    return ok


if inside_td():
    restore()
else:
    print('Run this inside the TouchDesigner textport:')
    print("  exec(open(r'C:\\Users\\James\\Desktop\\TOUCH\\restore_picture.py', encoding='utf-8').read())")
    self_check()
