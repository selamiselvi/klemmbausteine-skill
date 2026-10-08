"""Format 1.1: official LDraw parts measured from their geometry. Needs the parts library from setup_runtime.py."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/brick-models/scripts'))
from runtime import library_paths  # noqa: E402

HAVE_LIBRARY = library_paths()['ldraw'].is_file() and library_paths()['index'].is_file()


def model(parts, steps):
    return {'schema_version': '1.1', 'id': 'test', 'title': 'Test', 'description': 'Test model', 'author': 'Test',
            'license': 'UNLICENSED', 'parts': parts, 'steps': [{'title': f'Step {i}', 'parts': s} for i, s in enumerate(steps, 1)]}


def part(id, pid, color, x, y, z, rotation=0):
    return {'id': id, 'part': pid, 'color': color, 'x': x, 'y': y, 'z': z, 'rotation': rotation}


@unittest.skipUnless(HAVE_LIBRARY, 'official parts library not installed (run setup_runtime.py)')
class MeasuredParts(unittest.TestCase):
    def setUp(self):
        import ldraw
        self.analyze = ldraw.analyze

    def test_regular_brick(self):
        a = self.analyze('3001')
        self.assertEqual((a['width'], a['depth'], a['height']), (4, 2, 3))
        self.assertEqual(len(a['studs']), 8); self.assertEqual(len(a['receivers']), 8)

    def test_slope_has_studs_only_at_the_back(self):
        a = self.analyze('3039')
        self.assertEqual((a['width'], a['depth'], a['height']), (2, 2, 3))
        self.assertEqual(sorted(s[1] for s in a['studs']), [1, 1])
        self.assertLess(max(a['layers']['0,0']), 2, 'the sloped half must not fill the top layer')

    def test_tile_has_no_studs(self):
        a = self.analyze('3069b')
        self.assertEqual(a['height'], 1); self.assertEqual(a['studs'], []); self.assertEqual(len(a['receivers']), 2)

    def test_arch_receives_only_at_its_legs(self):
        a = self.analyze('3659')
        self.assertEqual(a['receivers'], [[0, 0], [3, 0]])
        self.assertEqual(a['layers']['1,0'], [2])

    def test_corner_brick_footprint(self):
        self.assertEqual(len(self.analyze('2357')['cells']), 3)

    def test_round_brick_with_hollow_stud(self):
        a = self.analyze('3062b')
        self.assertTrue(a['grid']); self.assertEqual(len(a['studs']), 1)

    def test_non_grid_part_is_rejected(self):
        self.assertFalse(self.analyze('30374')['grid'])   # a bar: no studs, no grid footprint


@unittest.skipUnless(HAVE_LIBRARY, 'official parts library not installed (run setup_runtime.py)')
class ValidationV11(unittest.TestCase):
    def setUp(self):
        from bricklib import ldraw, validate
        self.validate, self.ldraw = validate, ldraw
        self.base = model([part('base', '3035', '2', 0, 0, 0), part('arch', '3659', '4', 2, 0, 1),
                           part('tile', '3069b', '14', 2, 0, 4), part('slope', '3039', '70', 0, 2, 1, 180)],
                          [['base'], ['arch', 'slope'], ['tile']])

    def errors(self, m):
        r = self.validate(m)
        return r['passed'], ' '.join(r['errors'])

    def test_valid_model(self):
        ok, err = self.errors(self.base); self.assertTrue(ok, err)

    def test_nothing_holds_on_a_tile(self):
        m = copy.deepcopy(self.base); m['parts'].append(part('x', '3005', '15', 2, 0, 5)); m['steps'].append({'title': 'x', 'parts': ['x']})
        ok, err = self.errors(m); self.assertFalse(ok); self.assertIn('not connected to an earlier piece', err)

    def test_collision_inside_arch_opening(self):
        m = copy.deepcopy(self.base); m['parts'].append(part('x', '3005', '15', 3, 0, 1)); m['steps'].append({'title': 'x', 'parts': ['x']})
        ok, err = self.errors(m); self.assertFalse(ok); self.assertIn('Body collision', err)

    def test_unproduced_colour_is_an_error(self):
        import partdb
        p = partdb.part('3659')
        missing = next(c for c in partdb.index()['colors'] if partdb.index()['colors'][c]['rebrickable'] and c not in p['colors'])
        m = copy.deepcopy(self.base); m['parts'][1]['color'] = missing
        ok, err = self.errors(m); self.assertFalse(ok); self.assertIn('not recorded as produced', err)

    def test_rotation_moves_the_studs(self):
        import gridlib
        front = gridlib.Placed(part('s', '3039', '4', 0, 0, 0, 0)); back = gridlib.Placed(part('s', '3039', '4', 0, 0, 0, 180))
        self.assertEqual({s[1] for s in front.studs}, {1}); self.assertEqual({s[1] for s in back.studs}, {0})

    def test_ldraw_matches_legacy_placement_for_regular_bricks(self):
        import gridlib
        for rot, matrix in ((0, '1 0 0 0 1 0 0 0 1'), (90, '0 0 -1 0 1 0 1 0 0')):
            line = gridlib.Placed(part('b', '3001', '4', 3, 5, 6, rot)).ldraw_line()
            w, d = (4, 2) if rot == 0 else (2, 4)
            self.assertEqual(line, f'1 4 {(3 + w / 2) * 20:g} {-(6 + 3) * 8:g} {(5 + d / 2) * 20:g} {matrix} 3001.dat')

    def test_legacy_models_still_use_v1_rules(self):
        legacy = {'schema_version': '1.0', 'id': 'old', 'title': 'Old', 'description': 'Old', 'author': 'A', 'license': 'UNLICENSED',
                  'parts': [{'id': 'a', 'part': '3001', 'color': '4', 'x': 0, 'y': 0, 'z': 0, 'rotation': 0}],
                  'steps': [{'title': 'One', 'parts': ['a']}]}
        r = self.validate(legacy)
        self.assertTrue(r['passed']); self.assertEqual(r['schema_version'], '1.0')


@unittest.skipUnless(HAVE_LIBRARY, 'official parts library not installed (run setup_runtime.py)')
class Search(unittest.TestCase):
    def test_finds_slopes_with_produced_colours(self):
        import partdb
        r = partdb.search('slope 45 2 x 2', limit=5)
        self.assertEqual(r['results'][0]['id'], '3039')
        self.assertTrue(partdb.produced('3039', '70'))

    def test_colour_filter(self):
        import partdb
        ids = [x['id'] for x in partdb.search('arch 1 x 4', color_filter='Reddish Brown', limit=10)['results']]
        self.assertIn('3659', ids)


@unittest.skipUnless(HAVE_LIBRARY, 'official parts library not installed (run setup_runtime.py)')
class Sideways(unittest.TestCase):
    """Free placement, sideways studs, pins, clips and hinges (assembly.py)."""

    def setUp(self):
        import assembly
        from bricklib import validate
        self.assembly, self.validate = assembly, validate

    def build(self, parts, extra):
        inst = {p['id']: self.assembly.Instance(p) for p in parts}
        made = [f(inst) for f in extra]
        return model(parts + made, [[p['id'] for p in parts + made]])

    def index(self, inst, kind, female, axis=None):
        return next(i for i, c in enumerate(inst.connectors) if c['kind'] == kind and c['female'] == female
                    and (axis is None or tuple(round(v) for v in c['axis']) == axis))

    def test_connectors_are_measured(self):
        import ldraw
        kinds = lambda pid: sorted({(c['kind'], c['female']) for c in ldraw.analyze3d(pid)['connectors']})
        self.assertIn(('hole', True), kinds('3700'))
        self.assertEqual(kinds('3673'), [('pin', False)])
        self.assertIn(('bar', False), kinds('60478'))
        self.assertIn(('clip', True), kinds('4085c'))
        self.assertIn(('hinge', False), kinds('44301a'))
        side = [c for c in ldraw.analyze3d('87087')['connectors'] if c['kind'] == 'stud' and not c['female'] and c['axis'] == [0, 0, -1]]
        self.assertEqual(len(side), 1)

    def test_tile_on_a_side_stud(self):
        parts = [part('base', '3035', '72', 0, 0, 0), part('side', '87087', '15', 1, 1, 1)]
        snap = lambda inst: self.assembly.snap(inst['side'], self.index(inst['side'], 'stud', False, (0, 0, -1)), '3069b', '4', 0, 0, 'tile')
        r = self.validate(self.build(parts, [snap]))
        self.assertTrue(r['passed'], r['errors']); self.assertEqual(r['connections']['stud'], 2)

    def test_pin_joins_two_technic_bricks(self):
        parts = [part('base', '3035', '72', 0, 0, 0), part('a', '3700', '0', 4, 1, 1), part('b', '3700', '0', 4, 0, 1)]
        def pin(inst):
            i = next(i for i, c in enumerate(inst['a'].connectors) if c['kind'] == 'hole' and abs(c['pos'][2] - 20) < .5)
            return self.assembly.snap(inst['a'], i, '3673', '71', 0, 0, 'pin')
        r = self.validate(self.build(parts, [pin]))
        self.assertTrue(r['passed'], r['errors']); self.assertEqual(r['connections']['pin'], 2)

    def test_overhanging_handle_hits_studs_below(self):
        m = model([part('base', '3035', '72', 0, 0, 0), part('h', '60478', '15', 0, 3, 1, 0)], [['base', 'h']])
        r = self.validate(m)
        self.assertFalse(r['passed']); self.assertIn('blocked by h', ' '.join(r['errors']))

    def test_free_placement_rejects_skewed_matrix(self):
        m = model([part('base', '3035', '72', 0, 0, 0), {'id': 'f', 'part': '3005', 'color': '15', 'pos': [0, -8, 0], 'matrix': [2, 0, 0, 0, 1, 0, 0, 0, 1]}],
                  [['base', 'f']])
        self.assertFalse(self.validate(m)['passed'])


@unittest.skipUnless(HAVE_LIBRARY, 'official parts library not installed (run setup_runtime.py)')
class CompactSteps(unittest.TestCase):
    """Large models: steps stay in one working area (steps.py)."""

    def test_regroup_splits_a_scattered_step(self):
        import steps
        from bricklib import validate
        corners = [(0, 0), (30, 0), (0, 14), (30, 14)]
        parts = [part('base', '91405', '72', 0, 0, 0), part('base2', '91405', '72', 16, 0, 0), part('tie', '3034', '72', 12, 6, 1)]
        parts += [part(f'b{i}', '3001', '4', x, y, 1) for i, (x, y) in enumerate(corners)]
        parts += [part(f't{i}', '3001', '15', x, y, 4) for i, (x, y) in enumerate(corners)]
        m = model(parts, [['base', 'base2', 'tie'], [f'b{i}' for i in range(4)] + [f't{i}' for i in range(4)]])
        r = validate(m)
        self.assertTrue(r['passed'], r['errors']); self.assertTrue(any('step 2: new pieces spread' in w for w in r['warnings']))
        g = steps.regroup(m)
        r = validate(g)
        self.assertTrue(r['passed'], r['errors']); self.assertFalse(any('spread over' in w for w in r['warnings']))
        self.assertEqual(len(g['steps']), 6)               # two base areas, then one step per corner tower
        for s in g['steps'][2:]:                       # bottom brick before the brick on top of it
            self.assertEqual([p[0] for p in s['parts']], ['b', 't'])
        self.assertEqual(g['steps'][2]['title'], 'Step 2 (1/4)')


if __name__ == '__main__':
    unittest.main()
