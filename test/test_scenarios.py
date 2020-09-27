from unittest import TestCase
import ray
import pytest

from markets.realistic import *


class ScenarioTestClass(TestCase):

    @staticmethod
    def get_scenario() -> AbstractMarketScenario:
        return SynchronousMarketScenario()

    def test_scenario(self):

        sc = self.get_scenario()

        initial_prices = {
            'TSMC': 100,
            'NVDA': 200,
            'AAPL': 140,
            'SNOW': 400,
            'GE': '20'
        }
        mm = MarketMaker(initial_prices)

        warren = MomentumInvestor(name='Warren Buffet',
                                  portfolio={'TSMC': 5000, 'CASH': 200_000},
                                  market_maker=mm)

        sc.register_investors(warren)

        investors_list = sc.identify_investors()

        self.assertIsNotNone(investors_list[0])

        self.assertIn('Warren Buffet', investors_list[0])


@pytest.mark.skipif(reason="tests with ray actors only work in the IDE")
class RayScenarioTest(ScenarioTestClass):

    def setUp(self) -> None:
        ray.init()

    def tearDown(self) -> None:
        ray.shutdown()

    @staticmethod
    def get_scenario() -> AbstractMarketScenario:
        return RayMarketScenario()
