import unittest

from rwp.sspade import *
from rwp.environment import *
from rwp.terrain import *

__author__ = 'Lytaev Mikhail (mikelytaev@gmail.com)'

from rwp.terrain import geodesic_problem


class TestSSPade(unittest.TestCase):

    def test_terrain_max_propagation_angle__flat_terrain__expect_zero_angle(self):
        terrain = Terrain()

        max_angle = terrain_max_propagation_angle(terrain=terrain, distance_m=1000)

        self.assertAlmostEqual(max_angle, 0.0)

    def test_terrain_max_propagation_angle__linear_terrain__expect_zero_angle(self):
        mult = -0.1
        terrain = Terrain(lambda x: mult * x)
        expected_max_angle = abs(fm.degrees(fm.atan(mult)))

        max_angle = terrain_max_propagation_angle(terrain=terrain, distance_m=1000)

        self.assertAlmostEqual(max_angle, expected_max_angle)

    def test_create_terrain__default_params(self):

        terrain = Terrain()

        self.assertAlmostEqual(terrain.elevation(0), 0.0)
        self.assertAlmostEqual(terrain.elevation(100), 0.0)
        self.assertTrue(isinstance(terrain.ground_material(0), PerfectlyElectricConducting))
        self.assertTrue(isinstance(terrain.ground_material(100), PerfectlyElectricConducting))

    def test_create_terrain__constant_ground_material(self):

        terrain = Terrain(ground_material=VeryDryGround())

        self.assertTrue(isinstance(terrain.ground_material(0), VeryDryGround))
        self.assertTrue(isinstance(terrain.ground_material(0), VeryDryGround))
        self.assertTrue(not terrain.is_range_dependent_ground_material)

    def test_create_terrain__range_dependent_ground_material(self):
        def irregular_material(x):
            if x < 100:
                return FreshWater()
            else:
                return VeryDryGround()

        terrain = Terrain(ground_material=irregular_material)

        self.assertTrue(isinstance(terrain.ground_material(0), FreshWater))
        self.assertTrue(isinstance(terrain.ground_material(200), VeryDryGround))
        self.assertTrue(terrain.is_range_dependent_ground_material)

    def test_direct_geodesic_problem(self):

        res = geodesic_problem(60, 30, 90, [0, 100])

        self.assertTrue(len(res), 2)
        self.assertTrue(res[0], (60, 30))

    def test_inverse_geodesic_problem(self):
        lat1, long1 = 60, 30
        lat2, long2 = 70, 20

        res, x_grid = inv_geodesic_problem(lat1, long1, lat2, long2, 100)

        self.assertEqual(len(res), 100)
        self.assertEqual(len(x_grid), 100)
        self.assertAlmostEqual(res[0][0], lat1)
        self.assertAlmostEqual(res[0][1], long1)
        self.assertAlmostEqual(res[-1][0], lat2)
        self.assertAlmostEqual(res[-1][1], long2)


if __name__ == '__main__':
    unittest.main()