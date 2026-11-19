# /// script
# requires-python = ">=3.11"
# dependencies = ["manifold3d", "numpy", "trimesh"]
# ///
"""Build the rear-release latch prototype, in mm. Rear face is Z=0."""
import json
from pathlib import Path
import sys
import manifold3d as m
import trimesh

S = m.CrossSection
def xz(points, y0, y1):
    return S([points], m.FillRule.EvenOdd).extrude(y1-y0).rotate((90,0,0)).translate((0,y1,0))

def box(x,y,z,w,h,d):
    return m.Manifold.cube((w,h,d)).translate((x,y,z))

def build():
    # Tooth tip at x=0, panel seam at x=11.
    tooth = S([[(12,-5.5),(12,5.5),(0,11.5),(0,-11.5)]])
    blank = S.square((46,32)).translate((-16,-16))
    mask = S.square((31,44)).translate((-20,-22)) - tooth
    female = (blank ^ mask.offset(-.035)).extrude(12)
    male = (blank ^ (blank.offset(3)-mask).offset(-.035)).extrude(12)
    # Rear cavity around the tongue. Its roof grows inward from both
    # flanks at 45 degrees until the opening closes within the panel.
    cavity = xz([(-2,-1),(3.6,-1),(3.6,3.4),(.8,6.2),(-2,3.4)],-13,5.5)
    male -= cavity
    # A spring parallel to the bed. The free end is accessible at the rear.
    arm = box(.04,-7.5,0,1.55,13.6,3.0)
    ridge = xz([(.20,.35),(-.64,1.19),(-.64,1.69),(.20,2.53)],-6.6,-2.6)
    tongue = arm + ridge
    male += tongue
    # Match the actual ramps, allowing 0.10 mm vertically at either end.
    recess = xz([(.30,.15),(-.74,1.19),(-.74,1.69),(.30,2.73)],-6.75,-2.45)
    female -= recess
    # Chamfered, rear-open finger well adjacent to the catch; full stock
    # remains behind the pocket toward the logo face.
    well = xz([(-8,-1),(.5,-1),(.5,6.5),(-1.5,6.5),(-8,0)],-13,-6.85)
    female -= well
    assert (female ^ male).volume()<1e-7
    # Blocking material in both axial directions when the tongue is relaxed.
    for dz in (-.35,.35):
        assert (female ^ male.translate((0,0,dz))).volume()>.01
    return female,male,tongue

def mesh(solid):
    data=solid.to_mesh()
    return trimesh.Trimesh(data.vert_properties[:,:3],data.tri_verts)

def main(out):
    out.mkdir(parents=True,exist_ok=True)
    female,male,tongue=build()
    files=[]
    for solid,name in [(female,'Links-Gegenlager'),(male,'Rechts-Drueckzunge')]:
        t=mesh(solid)
        assert t.is_volume and t.is_watertight and t.body_count==1
        t.apply_translation(-t.bounds[0])
        path=out/(name+'.stl'); t.export(path)
        files.append(dict(path=str(path.resolve()),count=1,filaments=[1]))
    (out/'platte.json').write_text(json.dumps(dict(plates=[dict(plate_name='Rastprobe V3 - Rückseite',need_arrange=True,objects=files)])))
    # Three colours in the viewer; the tongue is integral to the right print.
    sections=[]
    for half in [False,True]:
        scene=[]
        for solid in (female,male-tongue,tongue):
            if half: solid=solid^box(-24,-4.6,-1,64,32,16)
            t=mesh(solid)
            scene.append([t.vertices.round(4).tolist(),t.faces.tolist()])
        sections.append(scene)
    (out/'mesh.json').write_text(json.dumps(sections,separators=(',',':')))

if __name__=='__main__':
    main(Path(sys.argv[1]))
