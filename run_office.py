#!/usr/bin/env python3
"""Open the reconstructed office in Isaac Sim; UI and real physics drive controls."""
import argparse,json,time,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--headless',action='store_true');parser.add_argument('--validate',action='store_true');parser.add_argument('--capture',action='store_true');parser.add_argument('--video',action='store_true');parser.add_argument('--exit-after',type=float,default=0);args,_=parser.parse_known_args()
from isaacsim import SimulationApp
import isaacsim
EXPERIENCE=Path(isaacsim.__file__).resolve().parent / "apps/isaacsim.exp.base.python.kit"
app=SimulationApp({'headless':args.headless,'hide_ui':args.headless,'open_usd':str(ROOT/'office_interactive.usda'),'renderer':'RaytracedLighting','sync_loads':True,'multi_gpu':False,'width':1600,'height':900,'window_width':1600,'window_height':1000},experience=str(EXPERIENCE))
import carb,omni.usd,omni.timeline,omni.kit.viewport.utility as vu
from pxr import Usd,UsdGeom,UsdPhysics,Gf
settings=carb.settings.get_settings();settings.set('/app/window/title','Isaac Sim | Office Real2Sim | Interactive reconstruction');settings.set('/physics/updateToUsd',True);settings.set('/physics/updateVelocitiesToUsd',True);settings.set('/app/runLoops/main/rateLimitEnabled',True);settings.set('/app/runLoops/main/rateLimitFrequency',60)
settings.set('/app/viewport/grid/enabled',False);settings.set('/rtx/indirectDiffuse/enabled',True);settings.set('/rtx/ambientOcclusion/enabled',True);settings.set('/rtx/post/aa/op',3);settings.set('/rtx/post/dlss/execMode',2);settings.set('/rtx/post/tonemap/op',6)
ctx=omni.usd.get_context()
for _ in range(100):app.update()
stage=ctx.get_stage();timeline=omni.timeline.get_timeline_interface();timeline.set_target_framerate(60);timeline.set_time_codes_per_second(60)
viewport=vu.get_active_viewport();viewport.set_texture_resolution((1600,900));viewport.set_active_camera('/World/Cameras/Workstations');ctx.get_selection().set_selected_prim_paths([],True)
manifest=json.loads((ROOT/'scene_manifest.json').read_text());specs={j['name']:j for j in manifest['joints']}
def target(name,value):
    j=specs[name];d=UsdPhysics.DriveAPI(stage.GetPrimAtPath(j['path']),'angular' if j['type']=='revolute' else 'linear');d.GetTargetPositionAttr().Set(float(max(j['lower'],min(j['upper'],value))))
    model=slider_models.get(name)
    if model and abs(model.as_float-value)>1e-5:model.set_value(value)
def step(n):
    for _ in range(n):app.update()
def capture(name,camera=None,settle=90):
    if camera:viewport.set_active_camera('/World/Cameras/'+camera)
    step(settle);out=ROOT/'renders'/name
    if out.exists():out.unlink()
    cap=vu.capture_viewport_to_file(viewport,file_path=str(out))
    for _ in range(200):
        app.update()
        if out.exists() and out.stat().st_size>1000:break
    if not out.exists():raise RuntimeError('Capture failed: '+str(out))
    print('CAPTURE '+str(out),flush=True)
def reset():
    timeline.stop();step(5)
    for name in specs:target(name,0)
    for model in slider_models.values():model.set_value(0)
    timeline.play()
def pose(body):
    m=UsdGeom.Xformable(stage.GetPrimAtPath(body)).ComputeLocalToWorldTransform(Usd.TimeCode.Default());p=m.ExtractTranslation();q=m.ExtractRotationQuat();return {'position':list(p),'quaternion':[q.GetReal(),*q.GetImaginary()]}
def yaw(body):
    m=UsdGeom.Xformable(stage.GetPrimAtPath(body)).ComputeLocalToWorldTransform(Usd.TimeCode.Default());return math.degrees(math.atan2(m[0][1],m[0][0]))
# Compact in-app panel, kept live by the main event loop.
panel=None;slider_models={}
if not args.headless:
    import omni.ui as ui
    panel=ui.Window('Office | Interactive objects',width=335,height=760)
    with panel.frame, ui.ScrollingFrame(horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF):
      with ui.VStack(spacing=6,height=0,width=260):
        ui.Label('OFFICE / REAL2SIM',height=26,style={'font_size':18,'color':0xffd7e6e6})
        ui.Label('Approximate reconstruction from 3 photographs',height=34,word_wrap=True,style={'font_size':12})
        with ui.HStack(height=30,spacing=6):
            ui.Button('Play',clicked_fn=timeline.play);ui.Button('Pause',clicked_fn=timeline.pause);ui.Button('Reset',clicked_fn=reset)
        ui.Separator(height=8)
        ui.Label('Cameras',height=22)
        for row in [('Workstations','ChairDetail'),('Storage','WasherDetail'),('Overview',)]:
          with ui.HStack(height=28,spacing=6):
            for name in row:ui.Button(name,clicked_fn=lambda n=name:viewport.set_active_camera('/World/Cameras/'+n))
        ui.Separator(height=8)
        for label,name in [('Washer door (degrees)','WasherDoor'),('Chair swivel (degrees)','ChairSwivel'),('Drawer A top (metres)','CabinetA_Drawer1'),('Drawer A middle (metres)','CabinetA_Drawer2'),('Drawer A bottom (metres)','CabinetA_Drawer3'),('Drawer B top (metres)','CabinetB_Drawer1'),('Drawer B middle (metres)','CabinetB_Drawer2'),('Drawer B bottom (metres)','CabinetB_Drawer3'),('Crane boom (degrees)','CraneBoom')]:
          with ui.VStack(height=43):
            ui.Label(label,height=18)
            sp=specs[name];slider=ui.FloatSlider(min=sp['lower'],max=sp['upper'],step=.01);slider.model.set_value(0);slider.model.add_value_changed_fn(lambda m,n=name:target(n,m.as_float));slider_models[name]=slider.model
        ui.Label('Play simulation before moving sliders.\nSelect objects in Stage to inspect physics.',height=40,word_wrap=True)
    panel.setPosition(1245,75)
    step(5)
    viewport_window=ui.Workspace.get_window('Viewport')
    for window_name in ['Content','Console','Stage','Property','Render Settings']:
        w=ui.Workspace.get_window(window_name)
        if w:w.visible=False
    step(5)
    if viewport_window:panel.dock_in(viewport_window,ui.DockPosition.RIGHT,.24)
# Render static closed state before simulation mutates the stage.
if args.capture:
    for name,cam in [('01_workstations_closed.png','Workstations'),('02_chair_detail.png','ChairDetail'),('03_storage.png','Storage'),('04_washer_closed.png','WasherDetail'),('05_overview.png','Overview')]:capture(name,cam)
if args.validate:
    report={'isaac_sim':'6.0.0.1','stage_open':True,'composition_errors':[str(e) for e in stage.GetCompositionErrors()],'joint_tests':[]}
    rest_poses={j['body']:pose(j['body']) for j in specs.values()}
    timeline.play();step(180)
    report['initial_joint_anchor_error_m']=max(math.dist(pose(b)['position'],r['position']) for b,r in rest_poses.items())
    for name,value in [('WasherDoor',-95),('ChairSwivel',55),('CabinetA_Drawer1',-.29),('CabinetA_Drawer2',-.23),('CabinetA_Drawer3',-.20),('CabinetB_Drawer1',-.28),('CabinetB_Drawer2',-.22),('CabinetB_Drawer3',-.18),('CraneBoom',10)]:
        sp=specs[name];before=pose(sp['body']);target(name,value);step(150);after=pose(sp['body'])
        if sp['type']=='prismatic':
            achieved=after['position'][1]-rest_poses[sp['body']]['position'][1];ok=abs(achieved-value)<.025
        elif sp['axis']=='Z':achieved=yaw(sp['body']);ok=abs(achieved-value)<4
        else:
            m=UsdGeom.Xformable(stage.GetPrimAtPath(sp['body'])).ComputeLocalToWorldTransform(Usd.TimeCode.Default());achieved=math.degrees(math.atan2(m[1][2],m[1][1]));ok=abs(achieved-value)<4
        report['joint_tests'].append({'name':name,'target':value,'measured':achieved,'passed':ok,'before':before,'after':after});print('JOINT_TEST '+json.dumps(report['joint_tests'][-1]),flush=True)
    report['all_joints_passed']=all(t['passed'] for t in report['joint_tests'])
    report['bodies_finite']=all(all(math.isfinite(v) for v in pose(b)['position']) for b in manifest['dynamic_bodies'])
    # Loose bottle should remain supported by the desk after several seconds.
    bottle_z=pose('/World/Props/GraspBottle')['position'][2];report['bottle_origin_z']=bottle_z;report['table_collision_passed']=.76<bottle_z<.83
    (ROOT/'validation_report.json').write_text(json.dumps(report,indent=2));print('VALIDATION_RESULT '+json.dumps({k:v for k,v in report.items() if k!='joint_tests'}),flush=True)
    if args.capture:
        capture('06_interactive_open.png','Workstations');capture('07_washer_open.png','WasherDetail')
    for name in specs:target(name,0)
    step(180)
if args.video:
    frames=ROOT/'renders'/'frames';frames.mkdir(exist_ok=True);viewport.set_active_camera('/World/Cameras/Workstations');timeline.play();step(60)
    for i in range(120):
        v=(1-math.cos(2*math.pi*i/119))/2;target('WasherDoor',-100*v);target('ChairSwivel',55*v);target('CabinetA_Drawer1',-.31*v);target('CabinetA_Drawer2',-.26*v);step(3)
        out=frames/f'{i:04d}.png';vu.capture_viewport_to_file(viewport,file_path=str(out))
        while not out.exists():app.update()
        if i%20==0:print(f'VIDEO_FRAME {i}',flush=True)
viewport.set_active_camera('/World/Cameras/Workstations');timeline.play();step(60)
print('OFFICE_READY '+str(ROOT/'office_interactive.usda'),flush=True)
if args.headless:app.close(wait_for_replicator=False)
else:
    deadline=time.monotonic()+args.exit_after if args.exit_after else float('inf')
    while app.is_running() and time.monotonic()<deadline:
        command_file=ROOT/'scene_command.json'
        if command_file.exists():
            try:
                commands=json.loads(command_file.read_text());command_file.unlink()
                for c in commands:
                    if c['action']=='target':target(c['name'],c['value'])
                    elif c['action']=='camera':viewport.set_active_camera('/World/Cameras/'+c['name'])
                    elif c['action']=='capture':capture(c['name'],c.get('camera'),c.get('settle',60))
                    elif c['action']=='play':timeline.play()
                    elif c['action']=='pause':timeline.pause()
                    elif c['action']=='reset':reset()
                (ROOT/'command_done.json').write_text(json.dumps({'completed_at':time.time(),'commands':commands}))
            except Exception as exc:print('COMMAND_ERROR '+str(exc),flush=True)
        app.update()
    app.close(wait_for_replicator=False)
