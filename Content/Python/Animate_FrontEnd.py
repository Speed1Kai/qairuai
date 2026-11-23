"""Low-cost scene animation for the separate front-end level."""
import unreal

ROOT='/Game/FrontEnd'
DRONE='/Game/Enemies/CityMachines/StrikeDrone/'
M=unreal.MaterialEditingLibrary

def material(name,smoke):
    assets=unreal.EditorAssetLibrary
    path=ROOT+'/'+name
    if assets.does_asset_exist(path):
        return assets.load_asset(path)
    mat=unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
    mat.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    def node(kind,x,y):
        return M.create_material_expression(mat,getattr(unreal,'MaterialExpression'+kind),x,y)
    def join(start,output,end,pin):
        assert M.connect_material_expressions(start,output,end,pin),(output,pin)
    def assign(expression,prop):
        assert M.connect_material_property(expression,'',prop)

    strength=node('ScalarParameter',-430,290)
    strength.set_editor_property('parameter_name','Strength')
    strength.set_editor_property('default_value',.30)
    color=node('VectorParameter',-560,-100)
    color.set_editor_property('parameter_name','Tint')
    color.set_editor_property('default_value',unreal.LinearColor(.28,.43,.50) if smoke else unreal.LinearColor(.16,.81,1.))
    if smoke:
        mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
        mat.set_editor_property('two_sided',True)
        panner=node('Panner',-880,40)
        panner.set_editor_property('speed_x',-.031)
        panner.set_editor_property('speed_y',.014)
        texture=node('TextureSample',-652,91)
        texture.set_editor_property('texture',assets.load_asset('/Game/CityDowntown/Textures/T_Smoke_Tiled_D'))
        join(panner,'',texture,'UVs')
        radial=node('SphereMask',-540,460)
        radius=node('ScalarParameter',-880,660)
        radius.set_editor_property('parameter_name','Radius')
        radius.set_editor_property('default_value',.5)
        softness=node('ScalarParameter',-880,720)
        softness.set_editor_property('parameter_name','Hardness')
        softness.set_editor_property('default_value',.02)
        join(radius,'',radial,'Radius')
        join(softness,'',radial,'Hardness')
        coords=node('TextureCoordinate',-920,450)
        center=node('Constant2Vector',-920,580)
        center.set_editor_property('r',.5)
        center.set_editor_property('g',.5)
        join(coords,'',radial,'A')
        join(center,'',radial,'B')
        shape=node('Multiply',-326,390)
        join(radial,'',shape,'A')
        join(texture,'R',shape,'B')
        alpha=node('Multiply',-124,304)
        join(shape,'',alpha,'A')
        join(strength,'',alpha,'B')
        assign(alpha,unreal.MaterialProperty.MP_OPACITY)
        assign(color,unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    else:
        x=node('Multiply',-120,0)
        join(color,'',x,'A')
        join(strength,'',x,'B')
        assign(x,unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    M.recompile_material(mat)
    assert assets.save_loaded_asset(mat)
    return mat

def add_scenery(mesh,light,body):
    def tag(actor,name):
        actor.tags=[unreal.Name(name)]
    def attach(part,owner):
        part.attach_to_actor(owner,'',unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,
                             unreal.AttachmentRule.KEEP_WORLD,False)
    light_data=(
        ('Overcast',(-124,117,248),(.66,.81,.94),56,660,125,.19),
        ('SkyRim',(106,-162,172),(.55,.69,.87),92,510,75,.26),
        ('GroundBounce',(95,188,18),(.69,.77,.85),28,460,90,.04),
    )
    for name,location,color,energy,radius,size,specular in light_data:
        c=light(name,location,color,energy,radius,size).point_light_component
        c.set_editor_property('specular_scale',specular)
    for index,(location,scale,yaw) in enumerate((
        ((-57,-290,144),.12,-24.),
        ((82,-355,185),.081,115.),
    )):
        aircraft=mesh('CityDrone'+str(index),location,DRONE+'Strike_Chassis',scale=(scale,)*3,yaw=yaw)
        tag(aircraft,'MenuDrone')
        for side in ('L','R'):
            rotor=mesh(f'CityDrone{index}Rotor{side}',location,DRONE+'Strike_Rotor'+side,scale=(scale,)*3,yaw=yaw)
            attach(rotor,aircraft)
            tag(rotor,'MenuRotor')
        lamp=(location[0]+4.8,location[1]+3.,location[2]+1.2)
        marker=mesh('CityDrone'+str(index)+'Navigation',lamp,'/Engine/BasicShapes/Sphere',
                    '/Game/LabTutorial/Industrial/M_DoorStatus_Red',(.012,.012,.012))
        attach(marker,aircraft)
    smoke=material('M_MenuSmoke',True)
    for index,(position,scaling) in enumerate((
        ((-138,-250,26),(3.2,1.18,1)),
        ((136,-230,45),(2.5,1.30,1)),
        ((23,-319,110),(3.0,1.63,1)),
        ((118,-153,9),(2.17,.73,1)),
    )):
        actor=mesh('CityMist'+str(index),position,'/Engine/BasicShapes/Plane',smoke,scaling,roll=90)
        actor.static_mesh_component.set_cast_shadow(False)
        tag(actor,'MenuSmoke')
    screen=material('M_MenuSignal',False)
    for index,(x,z,width) in enumerate(((-45,139,10.5),(211,169,6.5),(-93,58,3.8),(107,73,8.))):
        for row in range(2):
            actor=mesh(f'CityLED{index}Row{row}',(x,-378+row,z-row*1.75),'/Engine/BasicShapes/Cube',
                       screen,(width/100,.007,.007),roll=0)
            actor.static_mesh_component.set_cast_shadow(False)
            tag(actor,'MenuScreen')


