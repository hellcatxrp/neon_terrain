import types, math, numpy as np
from PIL import Image
ns = {'__name__': 'music_rack_lib'}
exec(open(r'C:\Users\James\Desktop\TOUCH\build_music_rack.py', encoding='utf-8').read(), ns)
sim = types.ModuleType('cycle_sim'); exec(ns['CYCLE_SIM'], sim.__dict__)


class Chan(list):
    def numpyArray(self): return np.array(self, dtype=np.float32)


class Node:
    def __init__(s): s.ch = {}; s.spec = [0.0] * 64
    def chan(s, n): return Chan([s.ch[n]]) if n in s.ch else None
    numChans = property(lambda s: 1); numSamples = property(lambda s: 64)
    def __getitem__(s, i): return Chan(s.spec)


class Rack:
    def __init__(s): s.f = Node(); s.sp = Node()
    def op(s, n): return {'vis_features': s.f, 'spec_shape': s.sp}.get(n)


rack = Rack(); state = {'music': 0.0, 'kick': 0.0, 'f': 0}
sim.S.clear(); sim.init(); sim.S['rng'] = np.random.default_rng(7); sim.respawn()
rng = np.random.default_rng(3)


def advance(seconds):
    for _ in range(max(1, int(round(seconds * 60)))):
        f = state['f']; t = f / 60; k = state['kick']
        state['music'] += (1 / 60) * (0.12 + 0.9 + 0.8 * k)
        k = 1.0 if (t % 0.5) < 1 / 60 else k * math.exp(-(1 / 60) / 0.16); state['kick'] = k
        rack.f.ch = {'time': state['music'], 'kick': k}
        u = np.linspace(0, 1, 64)
        spec = (0.85 * np.exp(-u * 4.5) * (0.55 + 0.45 * k)
                + 0.45 * np.exp(-((u - 0.42) / 0.09) ** 2) * (0.6 + 0.4 * math.sin(t * 2.3))
                + 0.3 * np.exp(-((u - 0.7) / 0.07) ** 2) * (0.5 + 0.5 * math.sin(t * 3.1 + 1))
                + 0.05 * rng.random(64))
        sp = np.clip(spec, 0, 1)
        for _ in range(2):
            pd = np.concatenate(([sp[0]], sp, [sp[-1]])); sp = pd[:-2] * 0.25 + pd[1:-1] * 0.5 + pd[2:] * 0.25
        rack.sp.spec = list(sp)
        sim.step(rack, f, 60); state['f'] += 1


def smooth(e0, e1, x):
    x = np.clip((x - e0) / (e1 - e0), 0, 1); return x * x * (3 - 2 * x)


def h21(q):
    q = np.mod(np.asarray(q, float) * np.array([123.34, 345.45]), 1.0)
    d = (q * (q + 34.345)).sum(-1, keepdims=True); q = q + d
    return np.mod(q[..., 0] * q[..., 1], 1.0)


def render(name, W=640, H=360, section=0.62, low=0.8, rms=0.9):
    S = sim.S; hist = S['hist'][..., 0]; arena = S['arena']
    st = hist[sim.CAP].astype(float)
    cam = st[0:3]; tgt = st[3:6]; head = st[6]; crash = st[7]
    cpos = st[8:10]; hpos = st[10:12]; CAP = int(st[12]); A = st[13]; Hh = st[15]; WALL = st[18]; CS = st[19]
    punch = state['kick']
    collapse = 1 - float(smooth(0.2, 0.85, crash))
    AA = np.array([[0.92, 0.95, 1], [0.3, 1, 0.82], [1, 0.24, 0.58], [1, 0.62, 0.18]])
    BB = np.array([[0.25, 0.5, 1], [0.4, 0.28, 1], [0.22, 0.42, 1], [0.92, 0.16, 0.3]])
    x = section * 3; i = int(min(math.floor(x), 2)); fr = float(smooth(0.35, 0.65, x - i))
    cA = AA[i] * (1 - fr) + AA[i + 1] * fr; cB = BB[i] * (1 - fr) + BB[i + 1] * fr
    FOCAL = 1.6
    fw = tgt - cam; fw /= np.linalg.norm(fw); rt = np.cross(fw, [0, 1, 0]); rt /= np.linalg.norm(rt); up = np.cross(rt, fw)
    ys, xs = np.mgrid[0:H, 0:W]; u = (xs + 0.5) / W; v = 1 - (ys + 0.5) / H
    sc = np.stack([(u - 0.5) * 1.7778, v - 0.5], -1)
    rd = fw * FOCAL + rt * sc[..., 0:1] + up * sc[..., 1:2]; rd /= np.linalg.norm(rd, axis=-1, keepdims=True)
    G = arena.shape[0]

    def specrow(row, uu):
        r = np.mod(row, CAP); xx = uu * 63; i0 = xx.astype(int); i1 = np.minimum(i0 + 1, 63)
        return hist[r, i0] * (1 - (xx - i0)) + hist[r, i1] * (xx - i0)

    def profile(s, a):
        uu = np.clip(np.abs(a), 0, 1); k = np.floor(s).astype(int)
        vv = specrow(k, uu) * (1 - (s - k)) + specrow(k + 1, uu) * (s - k)
        return np.clip(vv, 0, 1) ** 1.35 * (1 - smooth(0.8, 1, uu))

    def valid(s): return ((s >= 0) & (s > head - CAP) & (s <= head + 3)).astype(float)

    def trail(xz):
        f = (xz + 0.5 * A) / A * G - 0.5; ii = np.floor(f).astype(int); w = f - ii

        def tex(dx, dy):
            cx = np.clip(ii[..., 0] + dx, 0, G - 1); cy = np.clip(ii[..., 1] + dy, 0, G - 1)
            return arena[cy, cx, 0], arena[cy, cx, 1]
        (s00, a00), (s10, a10), (s01, a01), (s11, a11) = tex(0, 0), tex(1, 0), tex(0, 1), tex(1, 1)
        w00 = (1 - w[..., 0]) * (1 - w[..., 1]) * valid(s00); w10 = w[..., 0] * (1 - w[..., 1]) * valid(s10)
        w01 = (1 - w[..., 0]) * w[..., 1] * valid(s01); w11 = w[..., 0] * w[..., 1] * valid(s11)
        tot = w00 + w10 + w01 + w11; safe = np.maximum(tot, 1e-9)
        ss = np.stack([s00, s10, s01, s11]); ww = np.stack([w00, w10, w01, w11]); aa = np.stack([a00, a10, a01, a11])
        lo = np.where(ww > 0, ss, 1e9).min(0); hi = np.where(ww > 0, ss, -1e9).max(0)
        s = (ww * ss).sum(0) / safe; a = (ww * aa).sum(0) / safe
        pick = ww.argmax(0); split = (hi - lo) > 6
        s = np.where(split, np.take_along_axis(ss, pick[None], 0)[0], s)
        a = np.where(split, np.take_along_axis(aa, pick[None], 0)[0], a)
        cov = np.where(split, ww.max(0) / safe, tot)
        s = np.where(tot < 1e-4, -1.0, s)
        cov = np.where(tot < 1e-4, 0.0, cov)
        return cov, s, a

    def height(xz):
        cov, s, a = trail(xz)
        return np.where(cov > 0, profile(np.maximum(s, 0), a) * Hh * collapse * cov, 0)

    hA = 0.5 * A
    rdx = np.where(np.abs(rd[..., 0]) > 1e-6, rd[..., 0], 1e-6); rdz = np.where(np.abs(rd[..., 2]) > 1e-6, rd[..., 2], 1e-6)
    tx0 = (-hA - cam[0]) / rdx; tx1 = (hA - cam[0]) / rdx; tz0 = (-hA - cam[2]) / rdz; tz1 = (hA - cam[2]) / rdz
    tin = np.maximum(np.minimum(tx0, tx1), np.minimum(tz0, tz1)); tout = np.minimum(np.maximum(tx0, tx1), np.maximum(tz0, tz1))
    hmax = Hh * 1.02 * collapse + 0.001
    down = rd[..., 1] < -1e-5
    ny = np.where(down, -rd[..., 1], 1.0)
    ttop = np.where(down, np.maximum((cam[1] - hmax) / ny, 0), np.where(cam[1] > hmax, 1e9, 0))
    tfloor = np.where(down, cam[1] / ny, 1e9)
    t0 = np.maximum(np.maximum(tin, 0), ttop); t1 = np.minimum(tout, tfloor)
    act = (tin < tout) & (t0 < t1)
    slab = t1 - t0; maxstep = np.maximum(slab / 24, 0.02)
    t = t0.copy(); tprev = t0.copy(); hit = np.zeros_like(act)
    for _ in range(160):
        idx = act & ~hit
        if not idx.any():
            break
        p = cam + rd * t[..., None]
        hh = np.zeros_like(t); hh[idx] = height(p[idx][:, [0, 2]])
        nh = idx & (p[..., 1] <= hh + 1e-4); hit |= nh
        done = idx & ~nh & (t >= t1); act &= ~done
        mv = idx & ~nh & ~done
        tprev = np.where(mv, t, tprev)
        t = np.where(mv, np.minimum(t + np.minimum(np.maximum(t * 0.012, 0.02), maxstep), t1), t)
    lo_, hi_ = tprev.copy(), t.copy()
    for _ in range(6):
        m = 0.5 * (lo_ + hi_); p = cam + rd * m[..., None]; hh = np.zeros_like(m)
        hh[hit] = height(p[hit][:, [0, 2]]); below = p[..., 1] <= hh
        hi_ = np.where(hit & below, m, hi_); lo_ = np.where(hit & ~below, m, lo_)
    thit = np.where(hit, hi_, np.where(down, tfloor, 1e9))
    kind = np.where(hit, 1, np.where(down, 2, 0))
    s = np.zeros((H, W)); a = np.zeros((H, W)); hgt = np.zeros((H, W))
    p = cam + rd * np.minimum(thit, 400)[..., None]
    cov, ss, aa = trail(p[hit][:, [0, 2]])
    k1 = np.zeros((H, W), bool); k1[hit] = cov > 0.3
    kind = np.where(hit & ~k1, 2, kind)
    s[hit] = np.where(cov > 0.3, ss, 0); a[hit] = np.where(cov > 0.3, aa, 0)
    hgt[k1] = profile(np.maximum(s[k1], 0), a[k1]) * collapse

    def fwid(x):
        dx = np.abs(np.diff(x, axis=1, append=x[:, -1:])); dy = np.abs(np.diff(x, axis=0, append=x[-1:, :]))
        return dx + dy
    fwS = fwid(s) * (H / 720) ** -1 * (H / 720)   # derivative per output pixel
    fwA = fwid(a)
    tt = np.minimum(thit, 400); fog = np.exp(-tt * 0.03); pix = tt / (720 * FOCAL) * (720 / H)
    col = np.zeros((H, W, 3))
    age = head - s; near1 = 1 - smooth(0.35, 0.75, fwS)
    d1 = np.abs(np.mod(s + 0.5, 1) - 0.5); l1 = (1 - smooth(0.5 * fwS, 1.5 * fwS + 1e-9, d1)) * near1
    d8 = np.abs(np.mod(s / 8 + 0.5, 1) - 0.5) * 8
    l8 = (1 - smooth(0.5 * fwS, 1.5 * fwS + 1e-9, d8)) * (1 - near1) * (1 - smooth(3, 6, fwS))
    halo = np.exp(-d1 / np.maximum(fwS * 2, 0.03)) * near1 * 0.22
    ea = np.abs(np.abs(a) - 0.96); rail = (1 - smooth(0.5 * fwA, 1.5 * fwA + 1e-9, ea)) * 0.6 * (fwA <= 0.5)
    guard = (fwS <= 6).astype(float); fd = head - s
    front = (1 - smooth(0, 1.2 + fwS * 2, fd)) * (fd >= -0.5)
    tmix = smooth(0, 90, age)[..., None]; lc = cA * (1 - tmix) + cB * tmix
    derez = float(smooth(0.12, 0.7, crash))
    keep = (h21(np.stack([np.floor(s / 3), np.floor(a * 3 + 3)], -1)) >= derez).astype(float)
    bright = (0.45 + rms * 0.45) * (0.55 + hgt * 0.9) * fog
    rib = lc * ((l1 + l8 + halo + rail) * bright * keep * guard)[..., None]
    rib += (lc * 0.5 + 0.5) * (front * (1.2 + punch * 2) * fog * keep * guard)[..., None]
    rib += lc * (0.03 * fog * (0.3 + low))[..., None]
    col = np.where((kind == 1)[..., None], rib, col)
    g = np.abs(np.mod(p[..., [0, 2]] / 2 + 0.5, 1) - 0.5) * 2
    gl = (1 - smooth(pix * 0.8, pix * 2 + 1e-9, g.min(-1))) * (1 - smooth(0.08, 0.3, pix))
    inside = np.where((np.abs(p[..., 0]) < hA) & (np.abs(p[..., 2]) < hA), 1, 0.2)
    fl = cB * (gl * 0.22 * fog * inside)[..., None]
    dh = p[..., [0, 2]] - hpos; fl += cA * (np.exp(-(dh ** 2).sum(-1) * 0.35) * 0.12 * (crash <= 0))[..., None]
    col = np.where((kind == 2)[..., None], fl, col)
    sky = np.zeros((H, W, 3)) + [0.004, 0.004, 0.008]
    sky += cB * (np.exp(-np.abs(rd[..., 1]) * 8) * (0.03 + low * 0.12))[..., None]
    col = np.where((kind == 0)[..., None], sky, col)
    for tw in (tin, tout):
        ok = (tin < tout) & (tw > 0) & (tw < thit)
        wp = cam + rd * tw[..., None]; ok &= (wp[..., 1] >= 0) & (wp[..., 1] <= WALL)
        wpix = tw / (720 * FOCAL) * (720 / H); wf = np.exp(-tw * 0.03)
        top = 1 - smooth(wpix, wpix * 2.5 + 0.01, WALL - wp[..., 1])
        along = np.where(np.abs(wp[..., 0]) > np.abs(wp[..., 2]), wp[..., 2], wp[..., 0])
        vl = 1 - smooth(wpix, wpix * 2 + 1e-9, np.abs(np.mod(along / 4 + 0.5, 1) - 0.5) * 4)
        col += cB * (ok * (0.03 + top * 0.9 + vl * 0.1) * wf * (0.5 + 0.5 * wp[..., 1] / WALL))[..., None]

    def proj(P):
        vv = np.asarray(P, float) - cam; dep = vv @ fw
        return np.array([vv @ rt, vv @ up]) / max(dep, 1e-3) * FOCAL, dep
    if crash <= 0:
        hs, dep = proj([hpos[0], 0.45, hpos[1]])
        if dep > 0.1:
            r = 0.10 * FOCAL / dep; d = np.linalg.norm(sc - hs, axis=-1)
            col += np.array([1, 0.97, 0.92]) * (np.exp(-(d / r) ** 2) * (0.8 + punch))[..., None]
            col += cA * (np.exp(-d / (r * 2.5)) * 0.18 * (1 + punch))[..., None]
    else:
        tau = crash * CS; fade = (1 - crash) ** 1.5; c = np.array([cpos[0], 0.5, cpos[1]])
        cs, dep = proj(c)
        if dep > 0.1:
            rad = (0.6 + 4 * (1 - math.exp(-tau * 2))) * FOCAL / dep; d = np.linalg.norm(sc - cs, axis=-1)
            col += (np.array([1, 0.95, 0.85]) * 0.6 + cA * 0.4) * (np.exp(-(d / rad) ** 2) * (1 - crash) ** 3 * 1.5)[..., None]
        for i in range(48):
            hh = [float(h21([i, k])) for k in (1.7, 5.3, 9.1, 13.9)]
            dr = np.array([hh[0] - 0.5, 0.35 + hh[1] * 0.8, hh[2] - 0.5]); dr /= np.linalg.norm(dr)
            P = c + dr * (3 + hh[3] * 8) * (1 - math.exp(-tau * 1.6)) / 1.6; P[1] = max(P[1] - 1.2 * tau * tau, 0.02)
            ps, dep = proj(P)
            if dep > 0.1:
                r = 0.06 * FOCAL / dep; d = np.linalg.norm(sc - ps, axis=-1)
                col += (np.array([1, 0.95, 0.85]) * (1 - hh[1]) + cA * hh[1]) * ((np.exp(-(d / r) ** 2) + 0.25 * np.exp(-d / (r * 4))) * fade)[..., None]
        col += np.array([1, 0.9, 0.8]) * math.exp(-tau * 7) * 0.9
    vq = np.stack([u - 0.5, v - 0.5], -1); col *= (1 - (vq ** 2).sum(-1) * 0.9)[..., None]
    col = 1 - np.exp(-np.maximum(col, 0) * 1.4)
    Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).save(r'C:\Users\James\Desktop\TOUCH\_preview\%s.png' % name)
    print(name, 'mode', sim.S['mode'], 'crash', round(float(crash), 2), 's', round(float(head), 1))


if __name__ == '__main__':
    advance(9.0); render('cycle_chase')
    for _ in range(600):
        advance(1 / 60)
        if sim.S['mode'] == 'turn' and sim.S['turned'] > 0.6:
            break
    render('cycle_turn')
    for _ in range(60 * 90):
        advance(1 / 60)
        if sim.S['mode'] == 'crash':
            break
    advance(0.35); render('cycle_crash_early')
    advance(0.9); render('cycle_crash_overhead')
