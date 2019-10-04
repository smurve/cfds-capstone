import unittest
import numpy as np

from utils.statsutils import avg_over_axis


class AvgOverAxisTestCase(unittest.TestCase):
    def test_avg_over_axis(self):
        orig = np.array([[
            # -> [5, 4, 6, 5, 8]
            [8, 7, 5, 3, 9],
            [2, 1, 7, 7, 7],

            # -> [4, 2, 5, 4, 7]
            [4, 1, 1, 5, 8],
            [4, 3, 9, 3, 6],

            # -> [3, 7, 6, 4, 3]
            [1, 7, 3, 0, 0],
            [5, 7, 9, 8, 6]]])

        ret = avg_over_axis(orig, 1, 2)
        expected = [[
            [5., 4., 6., 5., 8.],
            [4., 2., 5., 4., 7.],
            [3., 7., 6., 4., 3.]]
        ]
        self.assertTrue((ret == expected).all())


if __name__ == '__main__':
    unittest.main()
