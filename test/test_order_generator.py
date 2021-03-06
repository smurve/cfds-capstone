import uuid
from unittest import TestCase

from markets.realistic import TriangularOrderGenerator, OrderType


class OrderGeneratorTest(TestCase):

    def setUp(self) -> None:
        client_id = uuid.uuid4()
        self.expire_in_seconds = 10
        self.split = .01
        self.generator = TriangularOrderGenerator(client_id=client_id)

    def test_bid_volume_and_number_correct(self):
        price = 200
        tolerance = .02
        n_shares = 600
        res = self.generator.create_orders(p=price, tau=tolerance, n=n_shares, order_type=OrderType.BID, n_orders=10)

        total_order_volume = sum([e[0] * e[1] for e in res])
        self.assertAlmostEqual(total_order_volume, price * n_shares, delta=1e-3 * total_order_volume)

        number_of_shares_from_res = .5 * len(res) * res[0][1]
        self.assertAlmostEqual(n_shares, number_of_shares_from_res, delta=.1 * n_shares)

        price_low = price * (1 - .5 * tolerance) + self.split
        self.assertAlmostEqual(price_low, res[0][0], delta=1e-2 * price_low)

        price_high = price * (1 + .5 * tolerance)
        self.assertAlmostEqual(price_high, res[-1][0], delta=1e-2 * price_high)

    def test_ask_volume_and_number_correct(self):
        price = 200
        tolerance = .02
        n_shares = 600
        res = self.generator.create_orders(p=price, tau=tolerance, n=n_shares, order_type=OrderType.ASK, n_orders=10)

        total_order_volume = sum([e[0] * e[1] for e in res])
        self.assertAlmostEqual(total_order_volume, price * n_shares, delta=1e-3 * total_order_volume)

        number_of_shares_from_res = .5 * len(res) * res[-1][1]
        self.assertAlmostEqual(n_shares, number_of_shares_from_res, delta=0.1 * n_shares)

        price_low = price * (1 - .5 * tolerance)
        self.assertAlmostEqual(price_low, res[0][0], delta=1e-2 * price_low)

        price_high = price * (1 + .5 * tolerance) - self.split
        self.assertAlmostEqual(price_high, res[-1][0], delta=1e-2 * price_high)
