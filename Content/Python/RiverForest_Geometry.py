"""Source geometry for the forest basin, flowing river and impact debris."""
from pathlib import Path
import math
import random

NEAR, FAR = 17780., 21530.
MIN_X, MAX_X = -33000., 44000.
WATER_Z = 1090.
BRIDGE_Y = (NEAR+FAR)*.5
GROUND = 2150.


def bounds(x):
    phase = (x-5850.) / 5500.
    fade = min(1., abs(x-5850.) / 5000.)
    offset = (340*math.sin(phase)+210*math.sin(phase*1.9))*fade
    return NEAR+offset, FAR+offset+140*math.sin(phase*.73)*fade


def hillside(x, y):
    dist = max(-1800-x, x-13200, -4500-y, 0)
    near_blend = max(0., min(1., (NEAR-y)/2150.))
    envelope = min(1., dist/4200.)*near_blend
    hill = (460+390*math.sin((x+2400)/3600.)*math.cos(y/4950.)
            +420*math.cos(y/6100.+x/8400.)+240*math.sin((x+y)/2000.)
            + 86*math.sin(x/630.)*math.cos(y/770.))
    return GROUND+envelope*hill-1.5


class Model:
    def __init__(self):
        self.faces = []

    def face(self, pts, material, uvs=None):
        if uvs is None:
            uvs = [(p[0]/450., p[1]/450.) for p in pts]
        self.faces.append((pts, material, uvs))

    def band(self, first, second, material, u0, u1, v0, v1):
        self.face((first[0], first[1], second[1], second[0]), material,
                  ((u0, v0), (u1, v0), (u1, v1), (u0, v1)))

    def write(self, file):
        names = sorted({m for _, m, _ in self.faces})
        file.with_suffix('.mtl').write_text(''.join(f'newmtl {n}\nKd .2 .2 .2\n' for n in names))
        index = 1
        with file.open('w', encoding='ascii') as out:
            out.write(f'mtllib {file.stem}.mtl\no {file.stem}\n')
            previous = None
            for pts, material, uvs in self.faces:
                for (x, y, z), (u, v) in reversed(tuple(zip(pts, uvs))):
                    out.write(f'v {x:.4f} {-y:.4f} {z:.4f}\nvt {u:.5f} {v:.5f}\n')
                if material != previous:
                    out.write(f'usemtl {material}\n')
                    previous = material
                for i in range(1, len(pts)-1):
                    out.write(f'f {index}/{index} {index+i}/{index+i} {index+i+1}/{index+i+1}\n')
                index += len(pts)


def ground_tile(rect):
    x0, x1, y0, y1 = rect
    nx, ny = math.ceil((x1-x0)/750), math.ceil((y1-y0)/750)
    model = Model()

    def point(i, j):
        x, y = x0+(x1-x0)*i/nx, y0+(y1-y0)*j/ny
        top, _ = bounds(x)
        if y1 == NEAR:
            y += (top-NEAR)*(j/ny)**6
        return x, y, hillside(x, y)-GROUND

    for i in range(nx):
        for j in range(ny):
            a, b, c, d = point(i,j), point(i+1,j), point(i+1,j+1), point(i,j+1)
            model.face((a,b,c), 'forest')
            model.face((a,c,d), 'forest')
    return model


def river(water=False):
    model = Model()
    steps = 132

    def section(x):
        a, b = bounds(x)
        if water:
            return [(x, a+590, WATER_Z-GROUND), (x, b-590, WATER_Z-GROUND)]
        phase = math.sin(x/560.)*55+math.sin(x/230.)*27
        return [(x, a, -1.5), (x, a+220, -120+phase), (x, a+585, -950+phase),
                (x, a+990, -1240+phase), (x, b-1000, -1250+phase),
                (x, b-620, -950-phase), (x, b-230, -160+phase), (x, b, -4.)]

    for i in range(steps):
        x0, x1 = MIN_X+(MAX_X-MIN_X)*i/steps, MIN_X+(MAX_X-MIN_X)*(i+1)/steps
        a, b = section(x0), section(x1)
        for j in range(len(a)-1):
            points = a[j], b[j], b[j+1], a[j+1]
            uv = ((i/steps, 0), ((i+1)/steps, 0), ((i+1)/steps, 1), (i/steps, 1)) if water else None
            model.face(points, 'water' if water else 'rock', uv)
    return model


def fir(seed, distant=False):
    rng = random.Random(seed)
    model = Model()
    trunk = [(0., 33.), (.11, 24.), (.27, 18.), (.48, 14.), (.69, 9.), (.85, 5.), (1., 1.4)]
    height = rng.uniform(1130, 1560)
    lean = rng.uniform(-32, 35)

    def trunk_point(t, radius, k):
        a = k*math.tau/7
        return (math.cos(a)*radius+t*t*lean, math.sin(a)*radius, height*t)

    for (t0,r0), (t1,r1) in zip(trunk,trunk[1:]):
        for k in range(7):
            a, b = trunk_point(t0,r0,k), trunk_point(t0,r0,k+1)
            c, d = trunk_point(t1,r1,k+1), trunk_point(t1,r1,k)
            model.face((a,b,c,d), 'bark', ((k/7,t0*2),((k+1)/7,t0*2),((k+1)/7,t1*2),(k/7,t1*2)))

    regions = ((179,36,453,325), (655,32,975,386), (308,406,658,801), (645,452,988,852))

    def card(cx, cy, z, direction, length, width, slope, roll):
        dx, dy = math.cos(direction), math.sin(direction)
        sx, sy = -dy*math.cos(roll), dx*math.cos(roll)
        dz = math.sin(roll)*width
        u0,v0,u1,v1 = rng.choice(regions)
        v0,v1 = 1-v1/1024., 1-v0/1024.
        u0,u1 = u0/1024.,u1/1024.
        model.face(((cx-sx*width,cy-sy*width,z-dz),
                    (cx+sx*width,cy+sy*width,z+dz),
                    (cx+dx*length+sx*width,cy+dy*length+sy*width,z+slope+dz),
                    (cx+dx*length-sx*width,cy+dy*length-sy*width,z+slope-dz)),
                   'needles', ((u0,v0),(u1,v0),(u1,v1),(u0,v1)))

    layers = 9 if distant else 17
    turn = rng.uniform(0,math.tau)
    for layer in range(layers):
        t = .17+.79*layer/(layers-1)
        wide = 315*(1-t)**.88
        branches = 4 if distant else 6
        turn += .93
        for j in range(branches):
            angle = turn+math.tau*j/branches+rng.uniform(-.29,.29)
            reach = wide*rng.uniform(.70,1.33)
            z = t*height+rng.uniform(-28,28)
            cx, cy = lean*t*t, 0.
            card(cx,cy,z,angle,reach*1.34,reach*.60,reach*.11,rng.uniform(-.56,.56))
            step = reach*.43
            card(cx+math.cos(angle)*step, cy+math.sin(angle)*step,z+4,
                 angle+rng.choice((-1.,1.))*.51, reach*.78,reach*.40,reach*.30,rng.uniform(-.6,.65))
            if not distant:
                card(cx+math.cos(angle)*step, cy+math.sin(angle)*step,z-24,
                     angle-.48, reach*.81,reach*.39,reach*.18,rng.uniform(-.73,.68))
    for a in (0,2.1,4.2):
        card(lean*.93,0,height*.91,a,90,47,height*.10,1.09)
    return model


def spall(seed, boulder=False):
    rng = random.Random(seed)
    m = Model()
    n = 9
    rings = []
    for factor, h in ((.81, 0), (1., .27), (.79, .63), (.38, .89)) if boulder else ((.88, 0), (1., .26), (.84, 1.)):
        row = []
        for j in range(n):
            a = j*math.tau/n
            rad = rng.uniform(.80,1.18)*factor*150
            row.append((math.cos(a)*rad, math.sin(a)*rad*.78,
                        h*(160 if boulder else 40)+rng.uniform(-10,10)))
        rings.append(row)
    mat = 'rock' if boulder else 'concrete'
    for a,b in zip(rings,rings[1:]):
        for i in range(n):
            j = (i+1)%n
            m.face((a[i],a[j],b[j]),mat)
            m.face((a[i],b[j],b[i]),mat)
    m.face(rings[-1],mat)
    return m


def generate(directory):
    directory.mkdir(parents=True, exist_ok=True)
    meshes = {
        'SM_ForestSlope_West':ground_tile((MIN_X,-1800,-4500,NEAR)),
        'SM_ForestSlope_East':ground_tile((13200,MAX_X,-4500,NEAR)),
        'SM_ForestSlope_South':ground_tile((MIN_X,MAX_X,-24100,-4500)),
        'SM_RiverGorge':river(),
        'SM_RiverCurrent':river(True),
        'SM_Fir_A':fir(73), 'SM_Fir_B':fir(519), 'SM_Fir_C':fir(842),
        'SM_Fir_Distance':fir(413, True),
        'SM_CliffTalus':spall(391,True), 'SM_CliffBroken':spall(82,True),
        'SM_ImpactSlab':spall(263), 'SM_ImpactShards':spall(331),
    }
    for name, model in meshes.items():
        model.write(directory/(name+'.obj'))
    return meshes.keys()
