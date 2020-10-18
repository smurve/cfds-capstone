import time
from unittest import TestCase

import numpy as np
import pytest
import ray

from markets.realistic import (
    AbstractMarketScenario, SynchronousMarketScenario, RayMarketScenario,
    ChartInvestor, USITMarket, MarketMaker)
from markets.realistic.BiasedMarketView import INTRINSIC_VALUE, BiasedMarketView
from markets.realistic.Clock import Clock
from markets.realistic.strategy import PriceValueStrategyFactory
from markets.realistic.ensembles.minimum import ensemble


class ScenarioTest(TestCase):

    def setUp(self) -> None:
        # logging.getLogger('ChartInvestor').setLevel('INFO')
        # logging.getLogger('MarketMaker').setLevel('INFO')
        pass

    @staticmethod
    def get_scenario(clock: Clock) -> AbstractMarketScenario:
        return SynchronousMarketScenario(clock)

    def test_minimum_ensemble(self):
        # TODO: Fix order execution
        np.random.seed(17)

        clock = Clock(n_seconds=60, n_minutes=60, n_hours=24, n_days=256)

        sc = self.get_scenario(clock)

        sc.register_ensemble(ensemble)

        for i in range(0):
            sc.tick(seconds=1)

        pass
        #  chart = sc.statisticians[0].get_chart_data

    def test_scenario(self):
        np.random.seed(17)

        clock = Clock(n_seconds=60, n_minutes=60, n_hours=24, n_days=256)

        sc = self.get_scenario(clock)

        market = USITMarket({'TSMC': 186.73, 'AAPL': 201.22, 'TSLA': 462.4}, noise=0.)

        initial_prices = {stock.name: round(stock.psi(0), 2) for stock in market.get_stocks()}

        market_makers = sc.register_market_makers(MarketMaker(initial_prices))
        self.assertIsNotNone(market_makers)

        biases = {INTRINSIC_VALUE: lambda v: 0.96 * v}
        biased_market_view = BiasedMarketView(market, biases)
        warren = ChartInvestor(market=biased_market_view,
                               name='Warren Buffet',
                               portfolio={'TSMC': 5000},
                               cash=200_000,
                               strategy_factory=PriceValueStrategyFactory(
                                   action_threshold=0.01
                               ))

        # Michael has a bias as to overestimate the intrinsic value (OK, I know he wouldn't - ever!)
        biases = {INTRINSIC_VALUE: lambda v: 1.04 * v}
        # biases = {INTRINSIC_VALUE: lambda v: np.random.normal(1.03 * v, v * noise)}
        biased_market_view = BiasedMarketView(market, biases)
        michael = ChartInvestor(market=biased_market_view,
                                name='Michael Burry',
                                portfolio={'TSMC': 5000},
                                cash=200_000,
                                strategy_factory=PriceValueStrategyFactory(
                                    action_threshold=0.01
                                ))

        investors = sc.register_investors(warren, michael)

        warren = investors[0]
        self.assertIsNotNone(warren)

        investors_list = sc.identify_investors()

        self.assertIsNotNone(investors_list[0])

        self.assertIn('Warren Buffet', investors_list[0])

        sc.tick(seconds=10)

        time.sleep(.1)

        # This is a magic number determined by the reproducible random involved in the stock prices
        expected_price = 190.27
        self.assertEqual(expected_price, market_makers[0].get_prices()['TSMC']['last'])

        order_book = market_makers[0].get_order_book()

        self.assertEqual(15, len(order_book['TSMC']))

        pass

        # TODO: Introduce reporting from the market maker
        # TODO: Introduce simple Momentum Investors
        # TODO: Investors may create market orders (Retail)
        # TODO: Introduce node- and stock-specific market makers
        # TODO: Introduce stop loss strategy for investors


@pytest.mark.skipif(reason="tests with ray actors only work in the IDE")
class RayScenarioTest(ScenarioTest):

    def setUp(self) -> None:
        ray.init()

    def tearDown(self) -> None:
        import time
        time.sleep(1)
        ray.shutdown()

    @staticmethod
    def get_scenario(clock: Clock) -> AbstractMarketScenario:
        return RayMarketScenario(clock)
