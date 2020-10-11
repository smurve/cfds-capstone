from copy import deepcopy
from typing import Tuple
from unittest import TestCase
from mock import patch

from markets.realistic import (Order, OrderType, ExecutionType, Clock,
                               MarketMaker, USITMarket, ChartInvestor, AbstractMarketMaker)
from markets.realistic import AbstractInvestor


class OrderExpiryTest(TestCase):

    def setUp(self) -> None:
        self.order = Order("anybody", order_type=OrderType.ASK,
                           execution_type=ExecutionType.LIMIT,
                           symbol='TSMC', amount=100, price=134, expires_at=10)
        self.symbols = {'TSMC': 100.0, 'NVDA': 200.0}

        self.market = USITMarket({'TSMC': 100., 'NVDA': 200.}, noise=0.)

    def given_market_maker(self) -> MarketMaker:
        return MarketMaker(self.market)

    def given_order(self, **kwargs):
        order = deepcopy(self.order)
        for item in kwargs:
            order.__setattr__(item, kwargs[item])
        if order.execution_type == ExecutionType.MARKET:
            order.price = None
        if not isinstance(order.other_party, str):
            order.other_party = str(order.other_party)
        return order

    def given_investor(self, symbol: str) -> AbstractInvestor:
        return ChartInvestor(market=self.market,
                             name='Michael Burry',
                             portfolio={symbol: 1000},
                             cash=200_000,
                             strategy_factory=None)

    def given_connected_actors(self) -> Tuple[AbstractInvestor, AbstractInvestor, AbstractMarketMaker]:
        market_maker = self.given_market_maker()
        inv1 = self.given_investor('TSMC')
        inv2 = self.given_investor('TSMC')
        market_maker.register_participant(inv1)
        market_maker.register_participant(inv2)
        inv1.register_participant(market_maker, symbol=inv1.get_stock_symbols()[0])
        inv2.register_participant(market_maker, symbol=inv2.get_stock_symbols()[0])
        return inv1, inv2, market_maker

    @patch.object(ChartInvestor, 'report_expiry')
    def test_immediate_expiry(self, report_expiry):
        """
        Assert that an unmatched order is not registered for later execution.
        Assert that the investor is immediately informed about that expiry.
        """
        investor, _, market_maker = self.given_connected_actors()
        order = self.given_order(other_party=investor.get_qname(), expires_at=0)
        market_maker.submit_orders([order], Clock())

        self.assertEqual(market_maker.get_order_book(), {'TSMC': {}, 'NVDA': {}})
        report_expiry.assert_called_with(order)

    @patch.object(ChartInvestor, 'report_expiry')
    def test_no_expiry(self, report_expiry):
        """
        Assert that an unmatched order is not registered for later execution.
        Assert that the investor is immediately informed about that expiry.
        """
        investor, _, market_maker = self.given_connected_actors()
        order = self.given_order(other_party=investor.get_qname(), expires_at=10)
        market_maker.submit_orders([order], Clock())

        order_book = market_maker.get_order_book()
        self.assertEqual(order_book, {'TSMC': {134: (100, 'a')}, 'NVDA': {}})
        report_expiry.assert_not_called()

    def test_expired_before_match(self):
        """
        Assert that a registered order is not matched but even removed, once recognized as expired.
        """
        investor, _, market_maker = self.given_connected_actors()
        market_maker: MarketMaker = market_maker

        ask = self.given_order(order_type=OrderType.ASK,
                               other_party=investor.get_qname(), expires_at=10)

        bid = self.given_order(order_type=OrderType.BID,
                               other_party=investor.get_qname(), expires_at=30)

        # When submitting both orders with 20 seconds inbetween
        market_maker.submit_orders([ask], Clock())
        market_maker.submit_orders([bid], Clock().tick(20))

        # then the ask order should be gone and the bid should be registered
        order_book = market_maker.get_order_book()
        self.assertEqual(order_book, {'TSMC': {134: (100, 'b')}, 'NVDA': {}})

        # then the ask candidate should have disappeared
        self.assertEqual(market_maker.candidates[OrderType.ASK],  {'TSMC': None, 'NVDA': None})

        # then the the bid order becomes the next bid candidate
        self.assertEqual(market_maker.candidates[OrderType.BID],  {'TSMC': bid, 'NVDA': None})

    def test_next_best_bid_if_best_is_expired(self):
        """
        Assert that the next best bid is matched if the best (the current candidate) is expired
        """
        buyer, seller, market_maker = self.given_connected_actors()
        market_maker: MarketMaker = market_maker

        bid1 = self.given_order(order_type=OrderType.BID, price=110,
                                other_party=buyer.get_qname(), expires_at=10)

        bid2 = self.given_order(order_type=OrderType.BID, price=100,
                                other_party=buyer.get_qname(), expires_at=50)

        ask = self.given_order(order_type=OrderType.ASK, execution_type=ExecutionType.MARKET,
                               other_party=seller.get_qname(), expires_at=10)

        # When submitting both orders with 20 seconds inbetween
        market_maker.submit_orders([bid1], Clock())
        market_maker.submit_orders([bid2], Clock())
        market_maker.submit_orders([ask], Clock().tick(20))

        # then the expired order should have disappeared completely
        self.assertEqual(market_maker.orders[OrderType.BID]['TSMC'], {})
        self.assertIsNone(market_maker.candidates[OrderType.BID]['TSMC'])

        # and the second order is executed
        expected_volume = 100
        expected_price = 100
        self.assertEqual(seller.get_portfolio(), {'TSMC': 1000 - expected_volume,
                                                  'CASH': 200_000 + expected_price * expected_volume})

    def test_expired_partial_remainder(self):
        """
        Assert that the next best bid is matched if the best (the current candidate) is expired
        """
        buyer, seller, market_maker = self.given_connected_actors()
        market_maker: MarketMaker = market_maker

        ask = self.given_order(order_type=OrderType.ASK, execution_type=ExecutionType.MARKET,
                               other_party=seller.get_qname(), expires_at=10, amount=50)

        bid = self.given_order(order_type=OrderType.BID, price=120, amount=100,
                               other_party=buyer.get_qname(), expires_at=0)

        # When submitting both orders
        market_maker.submit_orders([ask], Clock())
        market_maker.submit_orders([bid], Clock())

        # then 50 shares should have been turned over
        self.assertEqual(1050, buyer.get_portfolio()['TSMC'])

        # and the remainder of the bid is immediately expired
        self.assertEqual(market_maker.orders[OrderType.BID]['TSMC'], {})
        self.assertIsNone(market_maker.candidates[OrderType.BID]['TSMC'])
