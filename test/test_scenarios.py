from unittest import TestCase

import pytest
import ray

from markets.realistic import *
import test.test_helpers as helpers


class ScenarioTest(TestCase):

    @staticmethod
    def get_scenario() -> AbstractMarketScenario:
        return SynchronousMarketScenario()

    def test_scenario(self):

        sc = self.get_scenario()

        initial_stocks = [helpers.given_stock('TSMC', 186.)]
        mm = MarketMaker(initial_stocks)

        market_makers = sc.register_market_makers(mm)
        self.assertIsNotNone(market_makers)

        warren = MomentumInvestor(name='Warren Buffet',
                                  portfolio={'TSMC': 5000, 'CASH': 200_000},
                                  market_maker=mm)

        investors = sc.register_investors(warren)
        warren = investors[0]
        self.assertIsNotNone(warren)

        investors_list = sc.identify_investors()

        self.assertIsNotNone(investors_list[0])

        self.assertIn('Warren Buffet', investors_list[0])


@pytest.mark.skipif(reason="tests with ray actors only work in the IDE")
class RayScenarioTest(ScenarioTest):

    def setUp(self) -> None:
        ray.init()

    def tearDown(self) -> None:
        ray.shutdown()

    @staticmethod
    def get_scenario() -> AbstractMarketScenario:
        return RayMarketScenario()
