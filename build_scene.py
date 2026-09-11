"""Photo-guided, editable office reconstruction. Units metres, Z up.
Geometry/dimensions inferred from three reference photographs, not metric photogrammetry.
No remote assets; all geometry and textures generated locally.
"""
from pathlib import Path
import math, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pxr import Usd, UsdGeom, UsdShade, UsdLux, UsdPhysics, Gf, Sdf, Vt
ROOT=Path(__file__).resolve().parent
rng=np.random.default_rng(19)
for d in ['textures','renders','references']: (ROOT/d).mkdir(exist_ok=True)
# Reference photographs are not required at runtime and are not distributed.
# Procedural woven carpet: linear-light material sampled via sRGB texture.
n=1024; yy,xx=np.mgrid[:n,:n]; noise=np.asarray(Image.fromarray(np.float32(rng.normal(0,22,(256,256)))).resize((n,n),Image.Resampling.BILINEAR))
fiber=5*np.sin(xx*2.6)+6*np.sin(yy*2.1)+3*np.sin((xx+yy)*.6)
a=np.clip(111+noise+fiber,45,184)
Image.fromarray(np.uint8(np.stack([a*.93,a*.96,a],-1))).save(ROOT/'textures/carpet.png')
# Fine mesh textile used on the curved ergonomic backrest.
a=np.full((512,512,3),86,dtype=np.uint8); a[::5,:,:]=27; a[:,::5,:]=30
Image.fromarray(a).save(ROOT/'textures/mesh.png')
a=190+rng.normal(0,2,(512,512))+7*np.sin(np.arange(512)[None,:]*.13)+3*np.sin(np.arange(512)[None,:]*.8)
Image.fromarray(np.uint8(np.stack([a*1.04,a*.96,a*.78],-1).clip(0,255))).save(ROOT/'textures/wood.png')
font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
font=lambda s:ImageFont.truetype(font_path,s)
im=Image.new('RGB',(1024,576),(13,23,35));d=ImageDraw.Draw(im)
d.rectangle((35,32,990,70),fill=(27,43,59));d.text((58,38),'UNITREE  /  ROBOTICS LAB',font=font(21),fill=(168,190,206))
for i in range(17):
    c=[(79,174,165),(136,148,180),(189,155,101)][i%3]
    d.rectangle((58+(i%3)*22,112+i*21,260+int(rng.integers(20,270)),120+i*21),fill=c)
d.rounded_rectangle((595,112,963,505),16,fill=(23,37,51))
for i in range(12):d.line((615,155+i*25,943,155+i*25),fill=(37,53,65),width=1)
pts=[(615+i*8,360+int(70*math.sin(i*.21)-i*2.3)) for i in range(41)];d.line(pts,fill=(90,190,182),width=4)
d.text((616,123),'TELEMETRY',font=font(20),fill=(197,214,220))
im.save(ROOT/'textures/screen.png')
im=Image.new('RGB',(480,180),(14,22,25));d=ImageDraw.Draw(im);d.text((30,22),'0:59',font=font(75),fill=(173,229,226));d.text((275,45),'40 C\n1200',font=font(25),fill=(147,184,187));im.save(ROOT/'textures/washer_display.png')
S=Usd.Stage.CreateNew(str(ROOT/'office_interactive.usda'));UsdGeom.SetStageUpAxis(S,UsdGeom.Tokens.z);UsdGeom.SetStageMetersPerUnit(S,1)
S.SetTimeCodesPerSecond(60);S.SetStartTimeCode(0);S.SetEndTimeCode(600)
world=UsdGeom.Xform.Define(S,'/World');S.SetDefaultPrim(world.GetPrim())
world.GetPrim().SetCustomDataByKey('reconstruction','photo-guided approximate geometry; three photographs; no calibrated scale')
scene=UsdPhysics.Scene.Define(S,'/World/PhysicsScene');scene.CreateGravityDirectionAttr((0,0,-1));scene.CreateGravityMagnitudeAttr(9.81)
M={}; joints=[]; dynamic=[]
def material(name,c,rough=.5,metal=0,tex=None,emission=None):
    mat=UsdShade.Material.Define(S,'/World/Looks/'+name);sh=UsdShade.Shader.Define(S,str(mat.GetPath())+'/Shader');sh.CreateIdAttr('UsdPreviewSurface')
    sh.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*c));sh.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(rough);sh.CreateInput('metallic',Sdf.ValueTypeNames.Float).Set(metal)
    if emission:sh.CreateInput('emissiveColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*emission))
    if tex:
        uv=UsdShade.Shader.Define(S,str(mat.GetPath())+'/UV');uv.CreateIdAttr('UsdPrimvarReader_float2');uv.CreateInput('varname',Sdf.ValueTypeNames.Token).Set('st')
        t=UsdShade.Shader.Define(S,str(mat.GetPath())+'/Texture');t.CreateIdAttr('UsdUVTexture');t.CreateInput('file',Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath('./textures/'+tex));t.CreateInput('sourceColorSpace',Sdf.ValueTypeNames.Token).Set('sRGB');t.CreateInput('wrapS',Sdf.ValueTypeNames.Token).Set('repeat');t.CreateInput('wrapT',Sdf.ValueTypeNames.Token).Set('repeat');t.CreateInput('st',Sdf.ValueTypeNames.Float2).ConnectToSource(uv.ConnectableAPI(),'result');sh.GetInput('diffuseColor').ConnectToSource(t.ConnectableAPI(),'rgb')
    mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(),'surface');M[name]=mat;return mat
for args in [('White',(.76,.78,.78),.36),('Wall',(.71,.73,.74),.88),('Ceiling',(.7,.72,.73),.9),('Black',(.028,.035,.042),.46),('Mesh',(.04,.05,.055),.92,0,'mesh.png'),('Rubber',(.012,.014,.017),.83),('Silver',(.53,.57,.59),.23,.8),('Divider',(.45,.59,.61),.32),('Carpet',(.18,.2,.23),.96,0,'carpet.png'),('Wood',(.66,.59,.45),.8,0,'wood.png'),('Cardboard',(.36,.235,.115),.94),('Tape',(.48,.33,.17),.42),('Red',(.43,.018,.025),.37),('Blue',(.02,.075,.26),.47),('Green',(.06,.23,.1),.7),('Bottle',(.51,.66,.7),.17,.15),('Glass',(.017,.035,.045),.14,.35),('Screen',(.05,.08,.1),.45,0,'screen.png'),('Display',(.02,.04,.045),.3,0,'washer_display.png'),('Light',(.85,.89,.95),.3,0,None,(3,3.2,3.4)),('Blind',(.7,.72,.715),.94),('Paper',(.84,.82,.76),.91),('Yellow',(.69,.51,.13),.67)]:material(*args)
pm=UsdShade.Material.Define(S,'/World/Looks/Contact');p=UsdPhysics.MaterialAPI.Apply(pm.GetPrim());p.CreateStaticFrictionAttr(.75);p.CreateDynamicFrictionAttr(.6);p.CreateRestitutionAttr(.05)
def xf(path,pos=(0,0,0),rot=(0,0,0)):
    a=UsdGeom.Xform.Define(S,path.replace("-","n"));a.AddTranslateOp().Set(Gf.Vec3d(*pos));a.AddRotateXYZOp().Set(Gf.Vec3f(*rot));return a.GetPrim()
def bind(prim,mat):UsdShade.MaterialBindingAPI.Apply(prim).Bind(M[mat])
def collide(prim,mesh=False):
    UsdPhysics.CollisionAPI.Apply(prim)
    prim.AddAppliedSchema('PhysxCollisionAPI');prim.CreateAttribute('physxCollision:contactOffset',Sdf.ValueTypeNames.Float).Set(.002);prim.CreateAttribute('physxCollision:restOffset',Sdf.ValueTypeNames.Float).Set(0)
    if mesh:UsdPhysics.MeshCollisionAPI.Apply(prim).CreateApproximationAttr('convexHull')
def rigid(prim,mass,kin=False):
    r=UsdPhysics.RigidBodyAPI.Apply(prim);r.CreateKinematicEnabledAttr(kin);UsdPhysics.MassAPI.Apply(prim).CreateMassAttr(mass)
    if not kin:dynamic.append(str(prim.GetPath()))
def mesh(path,verts,faces,mat,uv=None,collision=False):
    m=UsdGeom.Mesh.Define(S,path.replace("-","n"));m.CreatePointsAttr(verts);m.CreateFaceVertexCountsAttr([len(f) for f in faces]);m.CreateFaceVertexIndicesAttr([i for f in faces for i in f]);m.CreateSubdivisionSchemeAttr('none');m.CreateDoubleSidedAttr(True)
    if uv:
        p=UsdGeom.PrimvarsAPI(m).CreatePrimvar('st',Sdf.ValueTypeNames.TexCoord2fArray,UsdGeom.Tokens.vertex);p.Set(uv)
    bind(m.GetPrim(),mat)
    if collision:collide(m.GetPrim(),True)
    return m.GetPrim()
def box(path,pos,size,mat='White',collision=True,rot=None):
    b=UsdGeom.Cube.Define(S,path.replace("-","n"));b.CreateSizeAttr(1);b.AddTranslateOp().Set(Gf.Vec3d(*pos))
    if rot:b.AddRotateXYZOp().Set(Gf.Vec3f(*rot))
    b.AddScaleOp().Set(Gf.Vec3f(*size));bind(b.GetPrim(),mat)
    if collision:collide(b.GetPrim())
    return b.GetPrim()
def roundbox(path,pos,size,mat='White',r=.025,collision=False):
    # Rounded rectangular prism in XY with real curved silhouette.
    w,d,h=size;r=min(r,w*.45,d*.45);outline=[]
    for cx,cy,start in [(w/2-r,d/2-r,0),(-w/2+r,d/2-r,90),(-w/2+r,-d/2+r,180),(w/2-r,-d/2+r,270)]:
        for a in np.linspace(start,start+90,7):outline.append((cx+r*math.cos(math.radians(a)),cy+r*math.sin(math.radians(a))))
    n=len(outline);v=[(x+pos[0],y+pos[1],z+pos[2]) for z in [-h/2,h/2] for x,y in outline];f=[list(reversed(range(n))),list(range(n,2*n))]+[[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)]
    return mesh(path,v,f,mat,collision=collision)
def cyl(path,pos,r,h,mat='Black',axis='Z',collision=False):
    b=UsdGeom.Cylinder.Define(S,path.replace("-","n"));b.CreateRadiusAttr(r);b.CreateHeightAttr(h);b.CreateAxisAttr(axis);b.AddTranslateOp().Set(Gf.Vec3d(*pos));bind(b.GetPrim(),mat)
    if collision:collide(b.GetPrim())
    return b.GetPrim()
def ball(path,pos,size,mat='Black',collision=False):
    b=UsdGeom.Sphere.Define(S,path.replace("-","n"));b.CreateRadiusAttr(1);b.AddTranslateOp().Set(Gf.Vec3d(*pos));b.AddScaleOp().Set(Gf.Vec3f(*size));bind(b.GetPrim(),mat)
    if collision:collide(b.GetPrim())
    return b.GetPrim()
def tube(path,pts,r,mat='Black',sides=10):
    vs=[]
    for i,p in enumerate(pts):
        t=np.array(pts[min(i+1,len(pts)-1)])-np.array(pts[max(i-1,0)]);t=t/np.linalg.norm(t);seed=np.array([0,0,1]) if abs(t[2])<.95 else np.array([1,0,0]);u=np.cross(t,seed);u/=np.linalg.norm(u);v=np.cross(t,u)
        for a in np.linspace(0,2*math.pi,sides,endpoint=False):vs.append(tuple(np.array(p)+r*(u*np.cos(a)+v*np.sin(a))))
    fs=[[i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j] for i in range(len(pts)-1) for j in range(sides)];fs.extend([list(reversed(range(sides))),list(range((len(pts)-1)*sides,len(pts)*sides))]);return mesh(path,vs,fs,mat)
def plane(path,corners,mat,repeat=1):return mesh(path,corners,[[0,1,2,3]],mat,[(0,0),(repeat,0),(repeat,repeat),(0,repeat)])
def torus(path,center,r,thick,mat='Black',axis='Y',start=0,end=2*math.pi):
    pts=[]
    for a in np.linspace(start,end,65):
        q=(r*math.cos(a),0,r*math.sin(a)) if axis=='Y' else (r*math.cos(a),r*math.sin(a),0)
        pts.append(tuple(center[i]+q[i] for i in range(3)))
    return tube(path,pts,thick,mat,12)
def joint(name,body,pivot,axis,lo,hi,typ='revolute',body0=None,local1=(0,0,0),stiffness=1200,damping=100):
    path='/World/Joints/'+name
    j=(UsdPhysics.RevoluteJoint if typ=='revolute' else UsdPhysics.PrismaticJoint).Define(S,path.replace("-","n"));j.CreateBody1Rel().SetTargets([body]);j.CreateAxisAttr(axis);j.CreateLocalPos0Attr(Gf.Vec3f(*pivot));j.CreateLocalPos1Attr(Gf.Vec3f(*local1));j.CreateLowerLimitAttr(lo);j.CreateUpperLimitAttr(hi);j.CreateCollisionEnabledAttr(False)
    if body0:j.CreateBody0Rel().SetTargets([body0])
    d=UsdPhysics.DriveAPI.Apply(j.GetPrim(),'angular' if typ=='revolute' else 'linear');d.CreateTypeAttr('force');d.CreateStiffnessAttr(stiffness);d.CreateDampingAttr(damping);d.CreateMaxForceAttr(1200);d.CreateTargetPositionAttr(0)
    joints.append(dict(name=name,path=path,body=body,type=typ,axis=axis,lower=lo,upper=hi));return j
# ROOM: 9 m x 8 m x 2.9 m; wall/window grid and individual carpet tiles.
xf('/World/Room');box('/World/Room/Floor',(0,0,-.065),(9.3,8.3,.12),'Carpet')
for ix in range(18):
 for iy in range(16):
    x=-4.5+ix*.5;y=-4+iy*.5
    plane(f'/World/Room/Carpet_{ix}_{iy}',[(x+.002,y+.002,0),(x+.498,y+.002,0),(x+.498,y+.498,0),(x+.002,y+.498,0)],'Carpet',1)
box('/World/Room/BackWall',(0,4.06,1.45),(9.2,.12,2.9),'Wall');box('/World/Room/LeftWall',(-4.56,0,1.45),(.12,8,2.9),'Wall');box('/World/Room/RightWall',(4.56,0,1.45),(.12,8,2.9),'Wall');box('/World/Room/FrontWall',(0,-4.06,1.45),(9.2,.12,2.9),'Wall')
for y in [-3.96,3.96]:box(f'/World/Room/Skirting_{y}'.replace('.','_'),(0,y,.055),(9,.025,.11),'White')
for i in range(6):
    x=-3.76+i*1.48
    box(f'/World/Room/Window_{i}',(x,3.975,1.81),(1.4,.015,1.72),'Light',False)
    box(f'/World/Room/Blind_{i}',(x,3.94,1.84),(1.39,.02,1.72),'Blind',False)
    cyl(f'/World/Room/Roller_{i}',(x,3.9,2.715),.031,1.44,'White','X')
    cyl(f'/World/Room/BlindBar_{i}',(x,3.906,.98),.015,1.4,'Silver','X')
    tube(f'/World/Room/PullCord_{i}',[(x+.67,3.9,2.65),(x+.67,3.9,1.4)],.003,'White')
for x in [-1.5,2.96]:box('/World/Room/Column_'+str(x).replace('.','_'),(x,3.66,1.45),(.43,.6,2.9),'Wall')
xf('/World/Room/Ceiling')
for ix in range(15):
 for iy in range(14):
    x=-4.2+ix*.6;y=-3.9+iy*.6
    box(f'/World/Room/Ceiling/Tile_{ix}_{iy}',(x,y,2.925),(.594,.594,.035),'Ceiling',False)
for ix,x in enumerate([-3,-.6,1.8,4.2]):
 for iy,y in enumerate([-2.1,.3,2.7]):
    box(f'/World/Room/Ceiling/Panel_{ix}_{iy}',(x,y,2.897),(1.16,.56,.012),'Light',False)
    light=UsdLux.RectLight.Define(S,f'/World/Lights/Panel_{ix}_{iy}');light.AddTranslateOp().Set((x,y,2.865));light.CreateWidthAttr(1.12);light.CreateHeightAttr(.53);light.CreateIntensityAttr(4500);light.CreateColorAttr((.9,.95,1))
for i,(x,y) in enumerate([(-2.4,1.5),(1.2,-.9),(3,2.1)]):
    box(f'/World/Room/Ceiling/Vent_{i}',(x,y,2.891),(.55,.55,.019),'Black',False)
    for j in range(14):box(f'/World/Room/Ceiling/Slat_{i}_{j}',(x-.26+j*.04,y,2.878),(.015,.54,.015),'Silver',False)
dome=UsdLux.DomeLight.Define(S,'/World/Lights/Ambient');dome.CreateIntensityAttr(100);dome.CreateColorAttr((.85,.9,1))
# Broad daylight enters through the blinded windows.
for i,x in enumerate([-3,0,3]):
    l=UsdLux.RectLight.Define(S,f'/World/Lights/Daylight_{i}');l.AddTranslateOp().Set((x,3.8,1.9));l.AddRotateXOp().Set(-90);l.CreateWidthAttr(2);l.CreateHeightAttr(1.3);l.CreateIntensityAttr(2400)
# DESKS AND TABLETOP PROPS
def monitor(p,x,y,z=.79):
    roundbox(p+'/Stand',(x,y,z+.012),(.25,.18,.024),'Black',.025)
    box(p+'/Neck',(x,y+.015,z+.115),(.04,.04,.21),'Black',False)
    box(p+'/Bezel',(x,y,z+.37),(.56,.035,.33),'Black',False,(-7,0,0))
    plane(p+'/Pixels',[(x-.259,y-.048,z+.222),(x+.259,y-.048,z+.222),(x+.259,y-.012,z+.51),(x-.259,y-.012,z+.51)],'Screen')
    cyl(p+'/Led',(x+.22,y-.021,z+.21),.002,.003,'Green','Y')
def keyboard(p,x,y,z=.792):
    roundbox(p+'/Keyboard',(x,y,z),(.41,.14,.02),'Black',.014)
    for row in range(5):
     for col in range(14):box(f'{p}/Key_{row}_{col}',(x-.187+col*.028,y-.053+row*.026,z+.013),(.021,.018,.006),'Rubber',False)
    ball(p+'/Mouse',(x+.29,y,z+.011),(.032,.054,.019),'Black')
def bottle(p,pos,dyn=False):
    xf(p,pos);cyl(p+'/Body',(0,0,.095),.033,.16,'Bottle',collision=dyn);ball(p+'/Shoulder',(0,0,.174),(.032,.032,.024),'Bottle');cyl(p+'/Neck',(0,0,.197),.014,.025,'Bottle');cyl(p+'/Cap',(0,0,.215),.016,.016,'Red');cyl(p+'/Label',(0,0,.1),.0335,.048,'Paper');cyl(p+'/Stripe',(0,0,.081),.034,.014,'Red')
    if dyn:rigid(S.GetPrimAtPath(p),.52)
def carton(p,pos,size=(.36,.3,.35),mat='Cardboard',dyn=False):
    a=xf(p,pos);box(p+'/Box',(0,0,size[2]/2),size,mat,True);box(p+'/Tape',(0,0,size[2]+.001),(.055,size[1],.003),'Tape',False);box(p+'/Label',(0,-size[1]/2-.002,size[2]*.55),(size[0]*.45,.003,.075),'Paper',False)
    if dyn:rigid(a,1.3)
def desk(p,x,y,clutter=True):
    xf(p,(x,y,0));roundbox(p+'/Top',(0,0,.766),(1.45,.72,.038),'White',.012,True)
    for side in [-1,1]:
        for dep in [-.30,.30]:box(p+f'/Leg_{side}_{dep}'.replace('.','_'),(side*.685,dep,.377),(.043,.043,.73),'White')
        box(p+f'/Foot_{side}',(side*.685,0,.032),(.043,.64,.043),'White')
    box(p+'/Apron',(0,.2,.67),(1.32,.035,.15),'White');box(p+'/Privacy',(0,.347,.99),(1.32,.014,.37),'Divider')
    for xx in [-.54,.54]:box(p+'/Clamp'+str(xx).replace('.','_'),(xx,.347,.802),(.04,.035,.075),'Silver',False)
    monitor(p+'/Monitor',-.16,.15);keyboard(p+'/Input',-.12,-.17)
    # Desktop tower under desk.
    box(p+'/Computer',(.49,.15,.26),(.19,.43,.49),'Black');box(p+'/ComputerFace',(.49,-.067,.27),(.16,.01,.43),'Rubber',False)
    cyl(p+'/Power',(.49,-.076,.44),.008,.006,'Blue','Y')
    tube(p+'/Cable',[(-.12,.16,.84),(-.35,.29,.79),(-.5,.29,.69),(-.45,.25,.14),(.45,.23,.03)],.005,'Black')
    if clutter:
        bottle(p+'/Bottle',(.52,-.16,.787))
        for k in range(3):box(p+f'/Papers_{k}',(.4,.1,.791+k*.006),(.18,.25,.005),'Paper',False, (0,0,-9+k*4))
        roundbox(p+'/Pouch',(-.55,-.1,.818),(.2,.14,.055),'Black',.025)
for n,(x,y) in enumerate([(-3.25,1.15),(-1.78,1.15),(-.31,1.15),(3.34,1.7),(-3.25,2.95),(-1.78,2.95),(.3,2.95),(1.77,2.95)]):desk(f'/World/Desks/Desk_{n+1}',x,y)
# Foreground desk intentionally keeps the drawers accessible.
# ERGONOMIC CHAIRS: five-star base, gas lift, curved woven mesh, lumbar frame.
def chair(p,x,y,yaw=0,interactive=False):
    # Movable swivel is fixed to the wheeled base for repeatable articulation tests.
    base=xf(p,(x,y,0));body=xf(p+'/SeatAssembly',(0,0,.43),(0,0,yaw))
    cyl(p+'/Lift',(0,0,.27),.027,.32,'Silver');cyl(p+'/LiftSleeve',(0,0,.18),.045,.18,'Black')
    for k in range(5):
        a=math.radians(90+k*72);cx,cy=.31*math.cos(a),.31*math.sin(a)
        tube(p+f'/Spoke_{k}',[(0,0,.18),(cx*.55,cy*.55,.125),(cx,cy,.095)],.021,'Black')
        cyl(p+f'/CasterStem_{k}',(cx,cy,.077),.018,.065,'Silver')
        for side in [-1,1]:cyl(p+f'/Wheel_{k}_{side}',(cx+side*.024,cy,.047),.045,.035,'Rubber','X')
    q=p+'/SeatAssembly';roundbox(q+'/Seat',(0,.015,.025),(.5,.47,.073),'Black',.095,True)
    for side in [-1,1]:
        tube(q+f'/ArmFrame_{side}',[(side*.23,.15,.0),(side*.29,.06,.075),(side*.29,-.12,.245)],.024,'Black')
        roundbox(q+f'/ArmPad_{side}',(side*.285,.025,.265),(.075,.32,.035),'Black',.035)
    # Curved back surface: y negative = back; recline increases with height.
    def backpt(u,v):
        width=.225*(1-.12*math.sin(v*math.pi));return (u*width,-.203-.14*v+.053*(u*u)+.035*math.sin(v*math.pi*2),.105+.61*v)
    vs=[];uv=[];nu,nv=24,34
    for j in range(nv+1):
     for i in range(nu+1):vs.append(backpt(-1+2*i/nu,j/nv));uv.append((i/nu*3,j/nv*4))
    fs=[[j*(nu+1)+i,j*(nu+1)+i+1,(j+1)*(nu+1)+i+1,(j+1)*(nu+1)+i] for j in range(nv) for i in range(nu)]
    mesh(q+'/WovenBack',vs,fs,'Mesh',uv)
    for side in [-1,1]:tube(q+f'/BackRail_{side}',[backpt(side,t) for t in np.linspace(0,1,35)],.02,'Black')
    for v in [0,1]:tube(q+f'/BackEdge_{v}',[backpt(t,v) for t in np.linspace(-1,1,25)],.02,'Black')
    tube(q+'/Spine',[(0,-.26,.08),(0,-.31,.24),(0,-.34,.47),(0,-.39,.7)],.025,'Black')
    roundbox(q+'/Lumbar',(0,-.22,.29),(.32,.054,.095),'Black',.02)
    hv=[];hu=[];hn=24;hm=24
    for j in range(hm+1):
     v=j/hm;wid=.192*math.sqrt(max(.035,1-(2*v-1)**2))
     for i in range(hn+1):
      u=-1+2*i/hn;hv.append((u*wid+.025*math.sin(v*math.pi),-.36-.025*math.sin(v*math.pi)+.035*u*u,.735+.235*v));hu.append((i/hn,j/hm))
    hf=[[j*(hn+1)+i,j*(hn+1)+i+1,(j+1)*(hn+1)+i+1,(j+1)*(hn+1)+i] for j in range(hm) for i in range(hn)]
    mesh(q+'/Headrest',hv,hf,'Mesh',hu)
    for side in [0,hn]:tube(q+f'/HeadrestEdge_{side}',[hv[j*(hn+1)+side] for j in range(hm+1)],.013,'Black')
    tube(q+'/HeadNeck',[(0,-.38,.68),(0,-.38,.81)],.018,'Silver')
    cyl(q+'/Tension',(0,-.1,-.05),.052,.1,'Black','X')
    if interactive:
        # Set zero-pose yaw to zero for clear drive coordinates.
        UsdGeom.Xformable(body).GetOrderedXformOps()[1].Set(Gf.Vec3f(0,0,0));rigid(body,9)
        joint('ChairSwivel',q,(x,y,.43),'Z',-175,175,stiffness=80,damping=20)
    return q
chair('/World/Chairs/HeroChair',-2.95,.02,-12,True)
for i,(x,y,a) in enumerate([(-1.4,.05,12),(-.2,.12,-20),(-3.25,2.12,2),(-1.7,2.05,-12),(1.8,2.07,10),(3.3,.68,-15)]):chair(f'/World/Chairs/Chair_{i}',x,y,a)
# THREE DRAWERS per cabinet, sliding on real USD prismatic joints.
def cabinet(p,x,y):
    xf(p,(x,y,0));box(p+'/Left',(-.215,0,.31),(.018,.5,.6),'White');box(p+'/Right',(.215,0,.31),(.018,.5,.6),'White');box(p+'/Back',(0,.245,.31),(.43,.014,.6),'White');box(p+'/Top',(0,0,.615),(.445,.51,.028),'White');box(p+'/Base',(0,0,.031),(.445,.51,.035),'Black')
    for i,(z,h) in enumerate([(.511,.165),(.343,.165),(.15,.195)]):
        q=p+f'/Drawer_{i+1}';b=xf(q,(0,0,z));box(q+'/Front',(0,-.255,0),(.392,.024,h-.012),'White');box(q+'/Floor',(0,-.005,-h/2+.018),(.385,.46,.018),'White')
        for side in [-1,1]:box(q+f'/Side{side}',(side*.195,0,0),(.014,.45,h-.035),'White')
        box(q+'/Back',(0,.225,0),(.392,.014,h-.035),'White')
        box(q+'/Recess',(0,-.269,h/2-.035),(.32,.007,.033),'Rubber',False);box(q+'/Handle',(0,-.287,h/2-.03),(.34,.026,.015),'Silver',False)
        rigid(b,2.2);joint(p.split('/')[-1]+f'_Drawer{i+1}',q,(x,y,z),'Y',-.34,0,typ='prismatic',stiffness=1200,damping=130)
        if i==0:box(q+'/Notebook',(0,-.03,-h/2+.037),(.22,.26,.02),'Blue',False)
cabinet('/World/Cabinets/CabinetA',-.53,1.03);cabinet('/World/Cabinets/CabinetB',-2.08,1.03)
# WASHING MACHINE: open aperture, recessed drum, door ring and hinge.
x,y=1.3,1.72;p='/World/Washer';xf(p,(x,y,0))
for side in [-1,1]:box(p+f'/Side{side}',(side*.293,0,.425),(.024,.60,.85),'White')
box(p+'/Top',(0,0,.842),(.61,.615,.028),'White');box(p+'/Rear',(0,.292,.423),(.57,.018,.82),'White');box(p+'/Base',(0,0,.035),(.57,.6,.05),'White')
box(p+'/ControlPanel',(0,-.298,.76),(.58,.035,.137),'White');box(p+'/BottomPanel',(0,-.298,.12),(.58,.035,.2),'White')
# Front square with circular opening composed as a mesh annulus.
verts=[];faces=[];zc=.445;rad=.234
for i,a in enumerate(np.linspace(0,2*math.pi,97)[:-1]):
    dx,dz=math.cos(a),math.sin(a);t=min(.288/max(abs(dx),1e-6),.224/max(abs(dz),1e-6));verts.extend([(rad*dx,-.318,zc+rad*dz),(t*dx,-.318,zc+t*dz)])
for i in range(96):faces.append([2*i,2*((i+1)%96),2*((i+1)%96)+1,2*i+1])
mesh(p+'/FrontShell',verts,faces,'White');torus(p+'/Gasket',(0,-.305,zc),.215,.023,'Rubber');cyl(p+'/DrumBack',(0,.16,zc),.204,.018,'Silver','Y');torus(p+'/DrumRim',(0,-.265,zc),.20,.012,'Silver')
# Drum side walls are open cylinders, with visible ribs and perforation dots.
for k in range(60):
    a=2*math.pi*k/60
    tube(p+f'/DrumLine_{k}',[(.199*math.cos(a),-.25,zc+.199*math.sin(a)),(.199*math.cos(a),.15,zc+.199*math.sin(a))],.0018,'Silver',6)
for row in range(7):
 for col in range(12):
    xx=-.14+col*.025;zz=zc-.12+row*.038
    if xx*xx+(zz-zc)**2<.18**2:ball(p+f'/Perforation_{row}_{col}',(xx,.148,zz),(.003,.001,.003),'Black')
box(p+'/DetergentTray',(-.182,-.321,.766),(.185,.014,.09),'White');box(p+'/TrayHandle',(-.182,-.335,.79),(.13,.015,.012),'Silver',False)
cyl(p+'/Dial',(.002,-.331,.775),.03,.019,'Silver','Y');plane(p+'/Display',[(.088,-.32,.719),(.276,-.32,.719),(.276,-.32,.8),(.088,-.32,.8)],'Display')
q=p+'/Door';b=xf(q,(-.238,-.34,zc));torus(q+'/OuterRing',(.238,0,0),.232,.024,'Black');torus(q+'/ChromeRing',(.238,-.016,0),.208,.012,'Silver');cyl(q+'/Window',(.238,-.007,0),.195,.018,'Glass','Y',True);torus(q+'/InnerLip',(.238,.011,0),.187,.007,'Black');ball(q+'/Handle',(.438,-.039,.028),(.027,.025,.083),'Black',False)
rigid(b,1.8);joint('WasherDoor',q,(x-.238,y-.34,zc),'Z',-112,0,stiffness=100,damping=18)
# Accessory stack on top, as in the photographs.
roundbox(p+'/Bag',(0,.07,.94),(.34,.24,.17),'Black',.045);tube(p+'/BagHandle',[(-.1,.07,1.01),(-.08,.07,1.095),(.08,.07,1.095),(.1,.07,1.01)],.009,'Black')
# STORAGE WALL / WOODEN FIVE-PANEL PARTITION
for i in range(5):
    p=f'/World/Partitions/Panel_{i}';xx=3.3-i*.69;yy=-2.96+(.10 if i%2 else 0);xf(p,(xx,yy,0),(0,0,5 if i%2 else -5));box(p+'/Core',(0,0,.98),(.65,.035,1.84),'Wood')
    for side in [-1,1]:box(p+f'/Post_{side}',(side*.33,0,.98),(.023,.043,1.9),'Black')
    for z in [.04,1.92]:box(p+'/Rail'+str(z).replace('.','_'),(0,0,z),(.67,.043,.023),'Black')
    for j in range(20):
     for face in [-1,1]:box(p+f'/Slat_{j}_{face}',(-.309+j*.0325,face*.023,.98),(.008,.008,1.82),'Paper',False)
    box(p+'/Foot',(0,0,.035),(.055,.46,.035),'Black');cyl(p+'/Caster',(0,-.2,.036),.033,.04,'Rubber','X')
# CRANE, with lifting boom and hook as articulated rigid bodies.
p='/World/Crane';xf(p,(3.92,-2.0,0));box(p+'/Mast',(0,0,1.0),(.11,.13,1.8),'Black')
for side in [-1,1]:
    box(p+f'/Leg_{side}',(side*.28,-.4,.105),(.095,1.05,.07),'Black');cyl(p+f'/Wheel_{side}',(side*.28,-.84,.065),.06,.06,'Rubber','X')
box(p+'/Crossbar',(0,.06,.15),(.67,.10,.08),'Black');q=p+'/Boom';b=xf(q,(0,0,1.68))
tube(q+'/Steel',[(0,0,0),(.14,-.65,.45),(.25,-1.27,.88)],.045,'Black',4);cyl(q+'/Pivot',(0,0,0),.065,.19,'Silver','X')
rigid(b,8);box(q+'/Collider',(.13,-.63,.43),(.085,1.52,.085),'Black',True,( -35,0,0));joint('CraneBoom',q,(3.92,-2,1.68),'X',-12,18,stiffness=5000,damping=300)
# Hook is visual attached to articulated boom. Hoisting rope is inextensible in this model.
tube(q+'/Cable',[(.25,-1.27,.86),(.25,-1.27,.17)],.004,'Silver');torus(q+'/Hook',(.25,-1.27,.09),.073,.014,'Red',axis='Y',start=.4,end=5.65)
# Cartons, cases, water packs beside the screen.
for i,(xx,yy,zz,size) in enumerate([(1.0,-3.4,0,(.48,.45,.45)),(1,-3.4,.45,(.44,.43,.4)),(1,-3.4,.85,(.4,.39,.37)),(1.52,-3.5,0,(.4,.42,.53)),(2.18,-3.53,0,(.49,.42,.39)),(2.18,-3.53,.39,(.48,.4,.35)),(2.18,-3.53,.74,(.4,.38,.43)),(.67,-2.82,0,(.31,.32,.32)),(2.9,-3.05,0,(.32,.3,.28))]):carton(f'/World/Storage/Box_{i}',(-xx,yy,zz),size,dyn=i==7)
for tier in range(4):
 for row in range(3):
  for col in range(5):bottle(f'/World/Storage/Water_{tier}_{row}_{col}',(-2.35-col*.072,-3.75+row*.073,.015+tier*.237))
for i in range(2):
    p=f'/World/Storage/EquipmentCase_{i}';xf(p,(.22-i*.47,-3.52,0));roundbox(p+'/Case',(0,0,.5),(.43,.48,1.0),'Black',.035,True)
    for z in [.07,.92]:box(p+f'/Band{z}'.replace('.','_'),(0,-.245,z),(.41,.012,.022),'Silver',False)
    tube(p+'/Handle',[(-.11,0,1.01),(-.11,0,1.07),(.11,0,1.07),(.11,0,1.01)],.013,'Black')
desk('/World/Desks/StorageBench',-3.61,-3.15)
UsdGeom.Xformable(S.GetPrimAtPath('/World/Desks/StorageBench')).GetOrderedXformOps()[1].Set(Gf.Vec3f(0,0,180))
carton('/World/Desks/StorageBench/Parcel',(.42,-.12,.79),(.24,.21,.19))
# Loose cables on floor are visual; not treated as rigid trip hazards.
tube('/World/Storage/FloorCable',[(-1,-3.37,.012),(.5,-2.73,.012),(2.6,-2.57,.012),(3.2,-2.2,.012),(2.7,-1.8,.012),(1.3,-2.1,.012),(.6,-1.8,.012),(1.15,-.7,.012),(2.5,.6,.012),(3.2,1.1,.1)],.007,'Black')
# Additional table clutter observed in photographs: bags, VR headset, books.
p='/World/Desks/Desk_1';roundbox(p+'/RedBag',(-.36,-.08,.82),(.41,.29,.065),'Red',.06)
p='/World/Desks/Desk_2';box(p+'/BlueGiftBag',(-.51,.02,.968),(.20,.12,.36),'Blue',False);tube(p+'/BagHandles',[(-.57,.018,1.15),(-.57,.018,1.22),(-.46,.018,1.22),(-.46,.018,1.15)],.004,'White')
p='/World/Desks/Desk_4';ball(p+'/VRHeadset',(.40,-.06,.862),(.15,.083,.075),'White');roundbox(p+'/VRFace',(.40,-.055,.835),(.25,.15,.065),'White',.06);tube(p+'/VRStrap',[(.26,-.02,.86),(.24,.15,.86),(.55,.15,.86),(.55,-.02,.86)],.015,'White')
bottle('/World/Props/GraspBottle',(.05,.86,.795),True)
# Cameras correspond to three reference viewpoints plus close-up articulation.
def camera(name,pos,target,focal=23):
    c=UsdGeom.Camera.Define(S,'/World/Cameras/'+name);c.CreateFocalLengthAttr(focal);c.CreateHorizontalApertureAttr(36);c.CreateVerticalApertureAttr(20.25);c.CreateClippingRangeAttr((.05,100));m=Gf.Matrix4d().SetLookAt(Gf.Vec3d(*pos),Gf.Vec3d(*target),Gf.Vec3d(0,0,1)).GetInverse();c.AddTransformOp().Set(m)
camera('Workstations',(3.15,-1.56,1.62),(-.9,1.65,.88),23)
camera('ChairDetail',(-4.1,-1.08,1.23),(-2.62,.63,.92),25)
camera('Storage',(0,.55,1.8),(0,-3.3,1.3),16)
camera('WasherDetail',(2.53,-.30,1.22),(1.2,1.62,.52),36)
camera('Overview',(4.20,-3.67,2.53),(-.45,.70,.78),19)
S.GetRootLayer().customLayerData={'cameraSettings':{'Perspective':{'position':Gf.Vec3d(3.96,-2.16,1.84),'target':Gf.Vec3d(-.8,1.6,1)}}}
S.GetRootLayer().Save();S.Export(str(ROOT/'office_interactive.usdc'))
report={'units':'metres','up_axis':'Z','estimated_room_size':[9,8,2.9],'source':'Three user office photographs; approximate procedural reconstruction, not a measured digital twin','joints':joints,'dynamic_bodies':dynamic,'stage':'office_interactive.usda','counts':{'prims':sum(1 for _ in S.Traverse()),'joints':len(joints),'dynamic_bodies':len(dynamic)}}
(ROOT/'scene_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report['counts']),flush=True)
