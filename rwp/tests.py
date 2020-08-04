import unittest

from rwp.sspade import *
from rwp.environment import *

__author__ = 'Lytaev Mikhail (mikelytaev@gmail.com)'


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


if __name__ == '__main__':
    unittest.main()