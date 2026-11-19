# /// script
# requires-python = ">=3.11"
# dependencies = ["manifold3d", "trimesh", "numpy"]
# ///
"""Twin tapered dovetail coupon. X crosses the seam, Y rises from the foot,
Z runs from the rear print surface towards the front. Dimensions in mm."""
import json
import math
import sys
from pathlib import Path

import manifold3d as m
import trimesh

DEPTH = 32
CENTRES = (22, 54)
FLANK_GAP = 0.035
FLARE = 0.65  # added to each half-width over the insertion stroke
PIN_X = -5.5
PIN_FLOOR = 12
PIN_LENGTH = 38
PIN_CLEARANCE = 0.08


def box(x, y, z, w, h, d):
    return m.Manifold.cube((w, h, d)).translate((x, y, z))


def polygon(points):
    return m.CrossSection([points], m.FillRule.EvenOdd)


def tooth(y, clearance):
    def profile(z):
        extra = FLARE * z / DEPTH
        return polygon([(1, y-5.5-extra), (-11, y-11.5-extra),
                        (-11, y+11.5+extra), (1, y+5.5+extra)]).offset(clearance)
    # Extruding towards the interior keeps the faces on Z=0 and Z=32.
    skin = 0.001
    first = profile(0).extrude(skin)
    last = profile(DEPTH).extrude(skin).translate((0, 0, DEPTH-skin))
    return (first + last).hull()


def pin_section(y, clearance, lead=0):
    half_width = 2.3 - 0.35*y/PIN_LENGTH - lead
    height = 2.5 - lead
    return polygon([(-half_width, 0), (half_width, 0), (half_width, height),
                    (0, height + math.sqrt(3)*half_width), (-half_width, height)]
                   ).offset(clearance).translate((PIN_X, PIN_FLOOR))


def end_face(section, y):
    return section.extrude(0.001).rotate((90, 0, 0)).translate((0, y, 0))


def pin_span(y1, y2, clearance=0, lead=0):
    return (end_face(pin_section(y1, clearance), y1+0.001) +
            end_face(pin_section(y2, clearance, lead), y2)).hull()


def key_and_socket():
    pin = pin_span(0, PIN_LENGTH-1) + pin_span(PIN_LENGTH-1, PIN_LENGTH, lead=.65)
    socket = pin_span(-1, PIN_LENGTH+.35, PIN_CLEARANCE)
    # Two local crush ribs at the entrance hold the key after insertion.
    # Both terminate within the female panel, before the first tooth.
    for side in (-1, 1):
        def edge(y):
            return PIN_X + side*(2.3 - .35*y/PIN_LENGTH)
        points = [(edge(y) + side*d, y) for y, d in
                  [(0.5, -.1), (1.3, .17), (3.2, .17), (5.2, -.1)]]
        rib = polygon(points).extrude(1.6).translate((0, 0, PIN_FLOOR))
        pin += rib
    return pin, socket


def build():
    left = box(-17, 0, 0, 17-FLANK_GAP, 69, DEPTH)
    right = box(FLANK_GAP, 0, 0, 12-FLANK_GAP, 69, DEPTH)
    for y in CENTRES:
        left -= tooth(y, FLANK_GAP)
        right += tooth(y, -FLANK_GAP)
    pin, socket = key_and_socket()
    return left-socket, right-socket, pin


def verify(left, right, pin):
    # Motion along the real assembly axes. The two small press ribs have
    # intentional interference in the entrance, which we measure separately.
    for step in range(65):
        assert (left ^ right.translate((0, 0, step/2))).volume() < 1e-6
    for step in range(PIN_LENGTH*2+1):
        pos = pin.translate((0, -step/2, 0))
        assert (pos ^ right).volume() < 1e-6
        contact = left ^ pos
        assert contact.volume() < 2
        if not contact.is_empty():
            assert contact.bounding_box()[4] < 5.3
    for dz in (-.3, .3):
        assert (pin ^ right.translate((0, 0, dz))).volume() > .01
    # Twisting a half in the face plane or tipping it around the seam
    # must hit the mating stock. These are geometric checks at fixed centres.
    for axis in ((0, 0, 1), (0, 1, 0)):
        for sign in (-1, 1):
            turned = right.translate((0, -34, -16)).rotate(
                tuple(sign*v for v in axis)).translate((0, 34, 16))
            assert (left ^ turned).volume() > .01


def export(out):
    out.mkdir(parents=True, exist_ok=True)
    solids = build()
    verify(*solids)
    parts, scene, section = [], [], []
    for solid, name in zip(solids, ('Nutteil', 'Doppelzapfen', 'Querstift')):
        raw = solid.to_mesh()
        model = trimesh.Trimesh(raw.vert_properties[:, :3], raw.tri_verts)
        assert model.is_watertight and model.is_volume and model.body_count == 1
        scene.append([model.vertices.round(4).tolist(), model.faces.tolist()])
        cut = (solid ^ box(PIN_X, -1, -1, 40, 72, 36)).to_mesh()
        section.append([cut.vert_properties[:, :3].round(4).tolist(), cut.tri_verts.tolist()])
        model.apply_translation(-model.bounds[0])
        path = out / (name+'.stl')
        model.export(path)
        parts.append(dict(path=str(path.resolve()), count=1, filaments=[1]))
    plate = dict(plate_name='V5 - Doppelfuehrung und Querstift', need_arrange=True, objects=parts)
    (out/'platte.json').write_text(json.dumps(dict(plates=[plate])))
    template = Path(__file__).with_name('keyed_joint.html').read_text()
    (out/'steckprobe-v5.html').write_text(template.replace('/*MESH*/[]', json.dumps([scene, section],separators=(',',':'))))


if __name__ == '__main__':
    export(Path(sys.argv[1]))
