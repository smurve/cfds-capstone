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

        market = USITMarket({'TSMC': 186.73, 'AAPL': 201.22, 'TSLA': 462.4})

        mm = MarketMaker(market)

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

        sc.tick()

        # TODO: Introduce Clock with seconds, minutes, hours, days - let 'tick' be configurable. Start with a minute
        # TODO: Tick should 'flow' to the investors
        # TODO: An investor asks the market maker for prices and values of her portfolio
        # TODO: Introduce simple Momentum and Value Investors
        # TODO: Investors create triangular limit orders (Institutional) or market orders (Retail)
        # TODO: Introduce node- and stock-specific market makers
        # TODO: Introduce order expiry
        # TODO: Introduce stop loss strategy for investors
        # TODO: Introduce central logging (return values from 'tick')
        # TODO: Introduce reporting from the market maker


@pytest.mark.skipif(reason="tests with ray actors only work in the IDE")
class RayScenarioTest(ScenarioTest):

    def setUp(self) -> None:
        ray.init()

    def tearDown(self) -> None:
        ray.shutdown()

    @staticmethod
    def get_scenario() -> AbstractMarketScenario:
        return RayMarketScenario()
