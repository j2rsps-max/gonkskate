import unittest
from compare_thug_params import compare
from thug_q import physics_tables, lookup, stat_definition

class PhysicsQTests(unittest.TestCase):
    def test_comments_and_override_resolution(self):
        q = '''// decorative /***** does not start a block
        standard_switch = (.9,1)
        STATS_SPEED = 3
        speed=100
        skater_physics={
        speed=200
        acceleration={ (10,20) STATS_SPEED switch=standard_switch limit=25 }
        }
        /* walk_physics={ speed=999 } */
        bike_physics={ speed=500 }
        // missing=5
        ; missing=5
        '''
        g,s=physics_tables(q)
        self.assertEqual(lookup('SPEED',g,s),'200')
        self.assertEqual(stat_definition(lookup('acceleration',g,s),g),
                         {'low':10.,'high':20.,'stat_index':3,'switch':[.9,1.],'limit':25.})
        result=compare(q,{'parameters':[{'name':'speed','value':200}, {'name':'missing','value':5}]})
        self.assertEqual(result['found_in_physics_q'],1)
        self.assertEqual(result['mismatch_count'],1)

    def test_unsupported_fields_fail(self):
        with self.assertRaises(ValueError):
            stat_definition('{(1,2) unknown=5}',{})

    def test_duplicate_and_unclosed_fail(self):
        for q in ('skater_physics={x=1\nx=2}', 'skater_physics={'):
            with self.assertRaises(ValueError): physics_tables(q)

if __name__=='__main__': unittest.main()
