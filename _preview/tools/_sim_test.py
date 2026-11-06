import types, math, time, numpy as np
ns = {'__name__': 'music_rack_lib'}
exec(open('build_music_rack.py', encoding='utf-8').read(), ns)
sim = types.ModuleType('cycle_sim'); exec(ns['CYCLE_SIM'], sim.__dict__)

class Chan(list):
    def numpyArray(self): return np.array(self, dtype=np.float32)
class Node:
    def __init__(s): s.ch = {}
    def chan(s, n): return Chan([s.ch[n]]) if n in s.ch else None
    numChans = property(lambda s: 1); numSamples = property(lambda s: 64)
    def __getitem__(s, i): return Chan(s.spec)
class Rack:
    def __init__(s): s.f = Node(); s.sp = Node(); s.sp.spec = [0.0]*64
    def op(s, n): return {'vis_features': s.f, 'spec_shape': s.sp}.get(n)
rack = Rack()
music = 0.0; kick = 0.0
turns = 0; prev_mode = 'straight'; runs = []; run_start = 0; worst = 0; total = 0
FR = 60*240
for f in range(FR):
    t = f/60
    loud = 0.3 if (t % 60) > 45 else 1.0
    energy = loud
    music += (1/60)*(0.12 + 0.9*energy**1.5 + 0.8*kick)
    if (t % 0.5) < 1/60 and loud > 0.5: kick = 1.0
    else: kick *= math.exp(-(1/60)/0.16)
    rack.f.ch = {'time': music, 'kick': kick}
    u = np.linspace(0,1,64)
    rack.sp.spec = list(np.clip(loud*(0.9*np.exp(-u*5)*(0.6+0.4*kick) + 0.35*np.exp(-((u-0.45)/0.1)**2)*(0.6+0.4*math.sin(t*2))), 0, 1))
    t0 = time.perf_counter(); sim.step(rack, f, 60); dt = time.perf_counter()-t0
    worst = max(worst, dt); total += dt
    m = sim.S['mode']
    if m == 'turn' and prev_mode != 'turn': turns += 1
    if m == 'crash' and prev_mode != 'crash':
        runs.append((round(t - run_start, 1), round(sim.S['s']*sim.SPACING, 1)))
    if prev_mode == 'crash' and m != 'crash': run_start = t
    prev_mode = m
print('crashes', sim.S['crashes'], 'turns', turns)
print('runs (seconds, trail length units):', runs)
print('python per frame: avg %.2f ms, worst %.1f ms' % (total/FR*1000, worst*1000))
np.save('_preview/state_arena.npy', sim.S['arena']); 

# diagnose: rerun and log crash context
sim.init(); music = 0.0; kick = 0.0; prev_mode='straight'
for f in range(60*120):
    t = f/60
    music += (1/60)*(0.12 + 0.9 + 0.8*kick)
    kick = 1.0 if (t % 0.5) < 1/60 else kick*math.exp(-(1/60)/0.16)
    rack.f.ch = {'time': music, 'kick': kick}
    pre = dict(mode=sim.S['mode'], pos=sim.S['pos'].copy(), th=sim.S['theta'], turned=sim.S['turned'])
    sim.step(rack, 100000+f, 60)
    if sim.S['mode']=='crash' and prev_mode!='crash':
        p = sim.S['pos']; th = sim.S['theta']
        q = p + sim._dir(th)*0.15
        lim = sim.ARENA/2-0.15
        wall = any(abs(c)>lim for k in (-0.85,0,0.85) for c in (q + sim._left(th)*sim.HALF*k))
        print('crash at', np.round(p,1), 'heading deg', round(math.degrees(th)%360), 'mode before', pre['mode'], 'turned', round(pre['turned'],2), 'wall' if wall else 'trail')
    prev_mode = sim.S['mode']
