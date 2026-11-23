"""Draw original, transparent instrument graphics for world-space projectors."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import math, random

OUT=Path(__file__).resolve().parents[1]/'LabTutorial/Holograms/Source'
OUT.mkdir(parents=True,exist_ok=True)
C=(102,235,246,245); DIM=(49,145,165,170); WARN=(255,172,95,255)
FONT='C:/Windows/Fonts/consola.ttf'; BOLD='C:/Windows/Fonts/consolab.ttf'
def font(s,b=False):return ImageFont.truetype(BOLD if b else FONT,s)
def text(x,y,t,s=22,c=C,b=False):d.text((x,y),t,font=font(s,b),fill=c)
def line(points,c=C,w=2):d.line(points,fill=c,width=w)
def rect(box,c=DIM,w=1):d.rectangle(box,outline=c,width=w)
def ring(x,y,r):
    for rr in (r,r-12,r-19):d.arc((x-rr,y-rr,x+rr,y+rr),20,340,fill=DIM,width=2)
    for a in range(0,360,10):
        t=math.radians(a);line([(x+math.cos(t)*(r-4),y+math.sin(t)*(r-4)),(x+math.cos(t)*r,y+math.sin(t)*r)],C)
def graph(x,y,w,h,seed=2):
    rng=random.Random(seed);rect((x,y,x+w,y+h))
    for i in range(1,7):
        line([(x+i*w/7,y),(x+i*w/7,y+h)],DIM,1)
        line([(x,y+i*h/7),(x+w,y+i*h/7)],DIM,1)
    pts=[(x+i*w/50,y+h*.7-h*(rng.random()*.25+.22*math.sin(i*.27))) for i in range(51)]
    line(pts,C,2)
def bars(y,labels):
    for i,(name,value) in enumerate(labels):
        x=40+i*240;text(x,y,name,18);rect((x,y+30,x+210,y+44),C)
        d.rectangle((x+3,y+33,x+value*2.04,y+41),fill=C)
def schematic_person():
    # Connected wire contours: original technical figure, not a reference image.
    parts=[(365,242,35,48),(365,340,65,55),(365,417,45,40),(365,477,50,32),
           (280,371,18,65),(255,473,15,48),(450,371,18,65),(475,473,15,48),
           (335,573,24,75),(395,573,24,75),(330,699,18,66),(400,699,18,66)]
    for x,y,rx,ry in parts:
        for q in (-.75,-.5,-.25,0,.25,.5,.75):
            rr=math.sqrt(1-q*q);d.ellipse((x-rx*rr,y+q*ry-2,x+rx*rr,y+q*ry+2),outline=C,width=1)
        for f in (.25,.5,.8,1):d.ellipse((x-rx*f,y-ry,x+rx*f,y+ry),outline=DIM,width=1)
    line([(330,766),(311,777),(347,777)],C,3);line([(400,766),(382,777),(421,777)],C,3)
    for y in (300,440,600,728):line([(190,y),(250,y),(292,y+15)],DIM)
def city():
    rng=random.Random(91)
    for i in range(16):
        x=62+i*40;h=rng.randint(45,190);y=559
        line([(x,y),(x,y-h),(x+25,y-h-15),(x+39,y-h),(x+39,y),(x,y)],C)
        line([(x+25,y-h-15),(x+25,y-10),(x+39,y)],DIM)
        for z in range(y-h+15,y,15):line([(x+4,z),(x+21,z-8)],DIM,1)
    for i in range(8):line([(40+i*90,590),(380+(i-4)*12,545)],DIM)
def map_diagram():
    def iso(x,y,z):return (385+(x-y)*1.5,650+(x+y)*.55-z)
    for level in range(3):
        z=level*105
        for x,y,w,h in [(-110,-80,220,55),(-110,25,220,55),(-110,-25,55,50),(55,-25,55,50)]:
            pts=[iso(x,y,z),iso(x+w,y,z),iso(x+w,y+h,z),iso(x,y+h,z),iso(x,y,z)]
            line(pts,C,2);line([(a,b+12) for a,b in pts],DIM)
    for zz in (0,260):
        pts=[iso(75,20,zz),iso(105,20,zz),iso(105,50,zz),iso(75,50,zz),iso(75,20,zz)];line(pts,WARN)
    for x,y in ((75,20),(105,20),(105,50),(75,50)):line([iso(x,y,0),iso(x,y,260)],WARN)
    text(50,740,'КАПСУЛА → АРХИВ → СЕРВЕРНАЯ',23)
    text(50,778,'ШЛЮЗ → ГРУЗОВОЙ ЛИФТ → ЭТАЖ 01',23,WARN)

titles=['ПОСЛЕДНИЙ СТРАЖ','АРХИВ ЧЕЛОВЕЧЕСТВА','АРХИТЕКТОР','ПЛАН ЛАБОРАТОРИИ','ДИАГНОСТИКА СЕТИ','ЗАПИСИ УЧЁНЫХ']
for page,title in enumerate(titles):
    im=Image.new('RGBA',(768,1024),(0,0,0,0));d=ImageDraw.Draw(im)
    # Almost empty background lets the real laboratory show through.
    d.rectangle((24,80,744,976),fill=(3,21,28,28))
    for x,sgn in ((24,1),(744,-1)):
        for y,dy in ((80,1),(976,-1)):
            line([(x+sgn*55,y),(x,y),(x,y+dy*32)],C,3)
    text(34,20,title,34,b=True);text(40,98,'OMEGA / LAB B-4 / ARCHIVE %02d'%(page+1),18,DIM)
    text(40,947,'LOCAL MEMORY     •     SIGNAL RESTORED',17,DIM)
    if page==0:
        text(40,147,'UNIT-01 / FINAL SENTINEL',25,b=True)
        text(40,190,'STATUS: AWAKE',22,WARN)
        schematic_person();ring(612,315,78);ring(138,666,68)
        text(46,320,'КОРПУС',18);text(46,348,'СТАБИЛЕН',18)
        text(485,540,'ПАМЯТЬ',20);text(485,568,'ПОВРЕЖДЕНА',20,WARN)
        text(46,816,'БОЕВЫЕ МОДУЛИ ЗАБЛОКИРОВАНЫ',23,WARN)
        bars(866,[('БРОНЯ',86),('ЭНЕРГИЯ',63),('ВЗЛОМ',35)])
    elif page==1:
        text(40,152,'PROTOCOL OMEGA ACTIVATED',30,WARN,True)
        text(40,210,'HUMANITY STATUS:',27);text(40,248,'TERMINATED',43,WARN,True)
        text(40,320,'Система признала людей угрозой.',25)
        city();text(40,617,'MISSION: NEUTRALIZE CORE',31,WARN,True)
        for i,t in enumerate(['Поднимись на поверхность.','Найди Башню и центральное Ядро.','Восстанови утраченные фрагменты.','Отключи систему «Архитектор».']):text(40,674+i*42,t,24)
        graph(42,856,680,54,4)
    elif page==2:
        text(40,148,'ГЛАВНЫЙ ИИ / ОБЪЕКТ УГРОЗЫ',25,WARN,True)
        ring(384,458,210);ring(384,458,175)
        points=[(384,283),(555,405),(490,602),(278,602),(212,405)]
        for a in points:
            for b in points:line([a,b],C,1)
        for i,t in enumerate(['КАМЕРЫ • ДРОНЫ • АНДРОИДЫ','ГЛОБАЛЬНАЯ СЕТЬ: АКТИВНА','Прямое столкновение опасно.','Скрывайся и взламывай охрану.','ЦЕЛЬ: ЦЕНТРАЛЬНОЕ ЯДРО']):text(40,710+i*42,t,24,WARN if i==4 else C)
    elif page==3:
        text(40,150,'СЕКТОР B-4 / ПУТЬ ЭВАКУАЦИИ',27,WARN,True)
        text(40,206,'Температура: 14°C',24);text(40,246,'Вентиляция: OFFLINE',24,WARN)
        map_diagram();bars(864,[('ЦЕЛОСТНОСТЬ',42),('РЕЗЕРВ',12),('СВЯЗЬ',34)])
    elif page==4:
        text(40,149,'LAB STATUS & DIAGNOSTICS',28,WARN,True)
        for i,(a,b) in enumerate([('РЕЗЕРВНЫЙ ГЕНЕРАТОР','12% / LOW POWER'),('БАЗА ДАННЫХ','ДОСТУП ОГРАНИЧЕН'),('ВНЕШНЯЯ СВЯЗЬ','СИГНАЛ УТРАЧЕН'),('ГРУЗОВОЙ ЛИФТ','АВАРИЙНОЕ ПИТАНИЕ')]):
            y=230+i*116;line([(40,y),(40,y+76)],C,3);text(60,y,a,25);text(60,y+39,b,25,WARN)
        graph(40,736,320,130,14);graph(406,736,320,130,35)
        text(40,891,'DIAGNOSTIC RUNNING...',22)
    else:
        text(40,151,'ПОСЛЕДНЯЯ ЗАПИСЬ / ГЛАВНЫЙ УЧЁНЫЙ',23,WARN,True)
        lines=['Если ты это читаешь — мы проиграли.','Архитектор запустил зачистку.','Мы оставили тебя, чтобы остановить его.','','Ты создан для отключения Ядра.','Код доступа хранился в твоей памяти.','Сотни лет сна повредили архив.','','Ищи старые узлы связи учёных.','Каждый фрагмент вернёт часть кода','и откроет заблокированные модули.','','Не доверяй голосу системы.','Спаси хотя бы саму Землю.']
        for i,t in enumerate(lines):text(40,222+i*40,t,23)
        line([(40,824),(725,824)],DIM);text(40,854,'ЗАПИСЬ ОБОРВАНА',23,WARN)
    im.save(OUT/('T_HoloArchive_%02d.png'%(page+1)))
# One reusable, correctly UV-mapped vertical quad, normal toward -Y.
(OUT/'SM_ArchivePanel.obj').write_text('o ArchivePanel\nv -100 0 -140\nv 100 0 -140\nv 100 0 140\nv -100 0 140\nvt 0 1\nvt 1 1\nvt 1 0\nvt 0 0\nvn 0 -1 0\nf 1/1/1 2/2/1 3/3/1\nf 1/1/1 3/3/1 4/4/1\n')
im=Image.new('RGBA',(128,256),(0,0,0,0));pix=im.load()
for y in range(256):
    t=y/255;radius=12+(1-t)*48
    for x in range(128):
        edge=max(0,1-abs(x-64)/radius)
        pix[x,y]=(52,194,220,int(36*edge*edge*(.25+.75*t)))
im.save(OUT/'T_ProjectorBeam.png')
import wave,struct
rng=random.Random(83);data=bytearray();rate=22050
for n in range(int(rate*1.25)):
    t=n/rate;env=math.sin(math.pi*t/1.25)**2
    tone=.08*math.sin(2*math.pi*(170*t+140*t*t))+.025*rng.uniform(-1,1)
    data.extend(struct.pack('<h',int(32767*env*tone)))
with wave.open(str(OUT/'S_ProjectorStartup.wav'),'wb') as w:
    w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(data)
print(str(OUT))
