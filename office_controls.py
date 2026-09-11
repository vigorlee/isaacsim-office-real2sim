"""Use from Isaac Sim Script Editor or a robot policy running inside Isaac Sim."""
from pxr import UsdPhysics
JOINTS={
    'washer':('WasherDoor','angular',-112,0),
    'chair':('ChairSwivel','angular',-175,175),
    'crane':('CraneBoom','angular',-12,18),
    **{f'drawer_{cab.lower()}{i}':(f'Cabinet{cab}_Drawer{i}','linear',-.34,0) for cab in 'AB' for i in range(1,4)}
}
def set_target(stage,object_name,value):
    """Angular values are degrees; drawer displacements are metres (negative opens)."""
    name,kind,lo,hi=JOINTS[object_name]
    if not lo<=value<=hi:raise ValueError(f'{object_name}: expected {lo} <= value <= {hi}')
    prim=stage.GetPrimAtPath('/World/Joints/'+name)
    if not prim:raise RuntimeError('Open office_interactive.usda before sending commands')
    UsdPhysics.DriveAPI(prim,kind).GetTargetPositionAttr().Set(float(value))
def open_all(stage):
    set_target(stage,'washer',-100)
    for cab in 'ab':
        for i in range(1,4):set_target(stage,f'drawer_{cab}{i}',-.28)
def close_all(stage):
    for name in JOINTS:set_target(stage,name,0)
