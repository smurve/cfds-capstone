from unittest import TestCase

import pytest
import ray
import numpy as np

from markets.realistic import *
from markets.realistic.BiasedMarketView import INTRINSIC_VALUE, BiasedMarketView
from markets.realistic.Clock import Clock


class ScenarioTest(TestCase):

    @staticmethod
    def get_scenario(clock: Clock) -> AbstractMarketScenario:
        return SynchronousMarketScenario(clock)

    def test_scenario(self):
        np.random.seed(17)

        clock = Clock(n_seconds=60, n_minutes=60, n_hours=24, n_days=256)

        sc = self.get_scenario(clock)

        market = USITMarket({'TSMC': 186.73, 'AAPL': 201.22, 'TSLA': 462.4})

        mm = MarketMaker(market)

        market_makers = sc.register_market_makers(mm)
        self.assertIsNotNone(market_makers)

        noise = .05
        biases = {INTRINSIC_VALUE: lambda v: np.random.normal(v, v*noise)}
        biased_market_view = BiasedMarketView(market, biases)
        warren = ChartInvestor(market=biased_market_view,
                               name='Warren Buffet',
                               portfolio={'TSMC': 5000},
                               cash=200_000)

        # Michael has a bias as to overestimate the intrinsic value
        biases = {INTRINSIC_VALUE: lambda v: np.random.normal(1.03 * v, v * noise)}
        biased_market_view = BiasedMarketView(market, biases)
        michael = ChartInvestor(market=biased_market_view,
                                name='Michael Burry',
                                portfolio={'TSMC': 5000},
                                cash=200_000)

        investors = sc.register_investors(warren, michael)

        warren = investors[0]
        self.assertIsNotNone(warren)

        investors_list = sc.identify_investors()

        self.assertIsNotNone(investors_list[0])

        self.assertIn('Warren Buffet', investors_list[0])

        sc.tick(seconds=10)

        pass

        # TODO: Introduce simple Momentum Investors
        # TODO: Investors may create market orders (Retail)
        # TODO: Introduce node- and stock-specific market makers
        # TODO: Handle order expiry at market maker and investor side
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
    def get_scenario(clock: Clock) -> AbstractMarketScenario:
        return RayMarketScenario(clock)
