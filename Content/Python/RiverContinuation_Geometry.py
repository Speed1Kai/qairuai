"""Match the two extended riverbanks to the existing ford and city terrain."""
import math
import sys
from pathlib import Path

from RiverForest_Geometry import FAR, GROUND, MIN_X, MAX_X, WATER_Z, Model, bounds

SOURCE = Path(__file__).resolve().parents[2]/'SourceAssets'
sys.path.insert(0,str(SOURCE/'CityReclaim'))
from Reclaim_Terrain import smooth, terrain_z

X0, X1 = -129000., 144000.
CHANNEL_START, CHANNEL_END = -121000., 136000.


def channel(x):
    a,b = bounds(x)
    distance = max(MIN_X-x,x-MAX_X,0.)
    shift = 0.
    if x<MIN_X:
        shift = 12000*smooth(distance/28500)-7300*smooth((distance-30000)/26500)
    elif x>MAX_X:
        shift = -11500*smooth(distance/30500)+7800*smooth((distance-32500)/26500)
    narrow = .29*smooth((distance-20000)/38000)
    trim = (b-a)*narrow*.5
    return a+shift+trim,b+shift-trim


def city_edge(x):
    base = 21750-54500*smooth((abs(x-5850)-32500)/22200)
    _,far = channel(x)
    return max(base,far-26)


def city_height(x,y):
    edge = city_edge(x)
    return -5.6+(terrain_z(x,y)+5.6)*smooth((y-edge)/6250)


def south_height(x,y):
    near,_ = channel(x)
    distance = max(MIN_X-x,x-MAX_X,0.)
    roll = 780+520*math.sin(x/5240+y/2980)+390*math.cos(y/2930-x/7680)
    ridge = 1760+1280*math.sin(x/9700+y/5800)**2
    return -4.+smooth(distance/12500)*smooth((near-y)/8800)*(roll+ridge)


def strip(model, rows, material):
    for a,b in zip(rows,rows[1:]):
        for i in range(len(a)-1):
            model.face((a[i],b[i],b[i+1],a[i+1]),material)


def grid(xs, top, bottom, rows, height, material):
    model=Model()
    columns=[]
    for x in xs:
        y0,y1=bottom(x),top(x)
        columns.append([(x,y0+(y1-y0)*j/rows,height(x,y0+(y1-y0)*j/rows))
                        for j in range(rows+1)])
    strip(model,columns,material)
    return model


def linear(a,b,steps):
    return [a+(b-a)*i/steps for i in range(steps+1)]


def bed_profile(x):
    a,b=channel(x)
    w=b-a
    waves=math.sin(x/560)*43+math.sin(x/213)*24
    z=WATER_Z-GROUND
    depth=smooth(min(x-CHANNEL_START,CHANNEL_END-x)/6600)
    bottom=z-250
    cross=[(a,-4.),(a+w*.075,-158+waves),
           (a+w*.16,z+95+waves),(a+w*.23,z-78+waves),
           (a+w*.36,bottom),(b-w*.36,bottom-22),
           (b-w*.24,z-85-waves),(b-w*.17,z+84-waves),
           (b-w*.071,-167-waves),(b,-5.6)]
    return [(y,-5.+(h+5.)*depth) for y,h in cross]


def bed_height(x,y):
    points=bed_profile(x)
    for (left,first),(right,second) in zip(points,points[1:]):
        if left<=y<=right:
            return first+(second-first)*(y-left)/(right-left)
    return -4.


def river_models():
    xs=sorted(set(linear(X0,CHANNEL_START,14)+linear(CHANNEL_START,MIN_X,160)+
                  linear(MIN_X,MAX_X,160)+linear(MAX_X,CHANNEL_END,167)+linear(CHANNEL_END,X1,14)))
    water,bed=Model(),Model()
    bed_columns,water_columns=[],[]
    for x in xs:
        a,b=channel(x)
        w=b-a
        z=WATER_Z-GROUND
        # The end sections narrow behind the bends. Below-water edges overlap
        # the rock bed so the moving water does not end at a visible seam.
        bed_columns.append([(x,y,h) for y,h in bed_profile(x)])
        water_columns.append(((x,a+w*.166,z),(x,b-w*.166,z)))
    strip(bed,bed_columns,'rock')
    for i,(a,b) in enumerate(zip(water_columns,water_columns[1:])):
        if xs[i]<CHANNEL_START or xs[i+1]>CHANNEL_END:
            continue
        u0,u1=((x-MIN_X)/(MAX_X-MIN_X) for x in xs[i:i+2])
        water.face((a[0],b[0],b[1],a[1]),'water',((u0,0),(u1,0),(u1,1),(u0,1)))
    return bed,water


def north_bank():
    model=Model()
    xs=linear(MIN_X,5210.,67)+linear(5210.,6490.,5)[1:]+linear(6490.,MAX_X,65)[1:]
    for a,b in zip(xs,xs[1:]):
        points=[]
        for x in (a,b):
            far=channel(x)[1]
            start=max(far-12,21610) if 5210.<=a and b<=6490. else far-12
            points.append([(x,y,-4.0) for y in (start,(start+23725)*.5,23725.)])
        strip(model,points,'forest')
    return model


def south_wings():
    model=Model()
    for x0,x1 in ((X0,MIN_X+75),(MAX_X-75,X1)):
        part=grid(linear(x0,x1,120),lambda x:channel(x)[0]+11,
                  lambda x:-52000.,48,south_height,'forest')
        model.faces.extend(part.faces)
    return model


def city_basin():
    return grid(linear(X0,X1,196),lambda x:176000.,city_edge,114,city_height,'forest')


def sidewalk():
    model=Model()
    # A beveled, low curb on the left with subtle settlement along the shoulder.
    rows=[]
    for i in range(9):
        y=-300+75*i
        damage=(math.sin(math.pi*i/8)**2)*math.sin(i*3.8)
        rows.append([(-167,y,1),(-161+damage*2.8,y,12+damage*1.1),
                     (-148,y,13),(131,y,10.1),(167+damage*2.5,y,2.5)])
    for a,b in zip(rows,rows[1:]):
        for i in range(len(a)-1):
            model.face((a[i],a[i+1],b[i+1],b[i]),'paving')
    return model


def generate(directory):
    directory.mkdir(parents=True,exist_ok=True)
    bed,water=river_models()
    objects={
        'SM_Riverbed_Continued':bed,'SM_RiverWater_Continued':water,
        'SM_RiverSouthWings':south_wings(),'SM_RiverNorthBank':north_bank(),
        'SM_CityBasin_Reshaped':city_basin(),'SM_WeatheredSidewalk':sidewalk(),
    }
    for name,model in objects.items():
        model.write(directory/(name+'.obj'))
    return objects.keys()
