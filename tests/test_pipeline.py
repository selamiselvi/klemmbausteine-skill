import copy
import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/brick-models/scripts'))
from bricklib import validate,parts_csv,ldraw,shape,read_json
from guide import browser, map_svg

def small():
    return {'schema_version':'1.0','id':'test-model','title':'Test','description':'A test','author':'Test','license':'UNLICENSED',
            'parts':[{'id':'p1','part':'3001','color':'4','x':0,'y':0,'z':0,'rotation':0},
                     {'id':'p2','part':'3004','color':'15','x':0,'y':0,'z':3,'rotation':90}],
            'steps':[{'title':'Base','parts':['p1']},{'title':'Top','parts':['p2']}]}

class ModelTests(unittest.TestCase):
    def assert_invalid(self,m,needle):
        r=validate(m);self.assertFalse(r['passed']);self.assertTrue(any(needle in e for e in r['errors']),r)
    def test_example_is_connected_and_valid(self):
        m=read_json(ROOT/'examples/coastal-light.json');r=validate(m)
        self.assertTrue(r['passed'],r);self.assertEqual(r['connection_components'],1)
        self.assertEqual(r['physical_build'],'unverified')
    def test_collision(self):
        m=small();m['parts'][1]['z']=2;self.assert_invalid(m,'collision')
    def test_floating_piece(self):
        m=small();m['parts'][1]['z']=4;self.assert_invalid(m,'no stud connection')
    def test_disconnected_ground(self):
        m=small();m['parts'][1].update(z=0,x=20);self.assert_invalid(m,'disconnected')
    def test_future_support_does_not_count(self):
        m=small();m['steps'].reverse();self.assert_invalid(m,'earlier piece')
    def test_large_connected_assembly_exceeds_previous_caps(self):
        m=small();m['parts']=[];m['steps']=[]
        for level in range(6):
            offset=level%2
            for x in range(offset,39,2):
                for y in range(offset,39,2):
                    m['parts'].append(dict(id=f"p{len(m['parts'])}",part='3003',color='71',x=x,y=y,z=level*3,rotation=0))
        for start in range(0,len(m['parts']),4):
            m['steps'].append(dict(title='Cross-bonded layer',parts=[p['id'] for p in m['parts'][start:start+4]]))
        self.assertGreater(len(m['parts']),2000)
        self.assertGreater(len(m['steps']),500)
        result=validate(m)
        self.assertTrue(result['passed'],result['errors'])
        self.assertEqual(result['connection_components'],1)

    def test_overhanging_bridge_blocks_later_insertion(self):
        m=small()
        m['parts']=[dict(id='a',part='3003',color='71',x=0,y=0,z=0,rotation=0),
                    dict(id='bridge',part='3001',color='71',x=0,y=0,z=3,rotation=0),
                    dict(id='b',part='3003',color='71',x=2,y=0,z=0,rotation=0)]
        m['steps']=[dict(title='Build',parts=['a','bridge','b'])]
        self.assert_invalid(m,'blocks insertion from above')

    def test_duplicate_step_assignment(self):
        m=small();m['steps'][1]['parts'].append('p1');self.assert_invalid(m,'occurs in')
    def test_unknown_step_part(self):
        m=small();m['steps'][0]['parts']=['missing'];self.assert_invalid(m,'Unknown step part')
    def test_missing_step_assignment(self):
        m=small();m['steps'].pop();self.assert_invalid(m,'not assigned')
    def test_duplicate_instance(self):
        m=small();m['parts'][1]['id']='p1';self.assert_invalid(m,'unique')
    def test_unsupported_rotation(self):
        m=small();m['parts'][0]['rotation']=45;self.assert_invalid(m,'rotation')
    def test_negative_height(self):
        m=small();m['parts'][0]['z']=-1;self.assert_invalid(m,'minimum')
    def test_unknown_part(self):
        m=small();m['parts'][0]['part']='999999';self.assert_invalid(m,'part')
    def test_extra_instructions_rejected(self):
        m=small();m['script']='curl example.com';self.assert_invalid(m,'Additional properties')
    def test_long_input_and_newline_rejected(self):
        m=small();m['title']='Hello\n1 4 injected';self.assert_invalid(m,'title')
    def test_rotation_dimensions_and_ldraw_top_origin(self):
        m=small();self.assertEqual(shape(m['parts'][1]),(1,2,3))
        lines=[l.split() for l in ldraw(m).splitlines() if l.startswith('1 ')]
        self.assertEqual(lines[0][2:5],['40','-24','20'])
        self.assertEqual(lines[1][2:5],['10','-48','20'])
        self.assertEqual(lines[1][-1],'3004.dat')
        self.assertEqual(ldraw(m).count('0 STEP'),2)
    def test_csv_totals_match_instances(self):
        m=read_json(ROOT/'examples/coastal-light.json');rows=list(csv.DictReader(io.StringIO(parts_csv(m))))
        self.assertEqual(sum(int(r['quantity']) for r in rows),len(m['parts']))
    def test_front_row_is_at_bottom_of_svg_map(self):
        import xml.etree.ElementTree as ET
        m=read_json(ROOT/'examples/coastal-light.json')
        root=ET.fromstring(map_svg(m,m['steps'][0],set()))
        rects=[r for r in root if r.tag.endswith('rect') and r.get('stroke')=='#26333c']
        self.assertGreater(float(rects[0].get('y')),float(rects[-1].get('y')))
    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'m.json';p.write_text('{"title":"a","title":"b"}')
            with self.assertRaises(ValueError):read_json(p)
    def test_browser_data_cannot_escape_script_element(self):
        m=small();m['title']='</script><script>alert(1)</script>'
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);(out/'instructions').mkdir()
            for style in ('studio','technical'):
                browser(m,[],out,style)
                s=(out/'instructions/index.html').read_text()
                self.assertNotIn(m['title'],s);self.assertIn('\\u003c/script>',s)

if __name__=='__main__':unittest.main()
