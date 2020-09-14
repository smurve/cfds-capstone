import datetime as dt
import uuid
from unittest import TestCase
from copy import deepcopy

from markets.orders import OrderType, Order
from markets.realistic import MarketMaker


class MarketMakerTest(TestCase):

    def setUp(self) -> None:
        self.order = Order(other_party=uuid.uuid4(), order_type=OrderType.ASK,
                           symbol='TSMC', amount=100, price=134, expiry=dt.datetime.now())
        self.symbols = ['TSMC']

    def given_market_maker(self):
        return MarketMaker(self.symbols)

    def given_order(self, **kwargs):
        order = deepcopy(self.order)
        for item in kwargs:
            order.__setattr__(item, kwargs[item])
        return order

    def test_register_participant_with_unknown_symbol(self):
        unknown_symbol = 'AAPL'
        mm = self.given_market_maker()
        try:
            mm.register_participant(uuid.uuid4(), {unknown_symbol: 100})
            self.fail("Should have raised ValueError")
        except ValueError as ve:
            self.assertTrue("Illegal portfolio" in str(ve))

    def test_order_with_unknown_symbol(self):
        unknown_symbol = 'AAPL'
        order = self.given_order(symbol=unknown_symbol)
        mm = self.given_market_maker()
        try:
            mm.submit_orders(unknown_symbol, [order])
            self.fail("Should have raised ValueError")
        except ValueError as ve:
            self.assertTrue("Illegal order" in str(ve))
        try:
            mm.submit_orders('TSMC', [order])
            self.fail("Should have raised ValueError")
        except ValueError as ve:
            self.assertTrue("Illegal order" in str(ve))

    def test_initial_ask(self):
        order = self.given_order()
        symbol = order.symbol
        mm = self.given_market_maker()
        mm.submit_orders(order.symbol, [order])
        self.assertEqual(mm.lowest_ask[symbol], order)
        self.assertEqual(mm.ask[order.symbol][order.price][0], order)

        # An equal bid won't update the high, yet gets registered for later matching
        other_order = self.given_order(order_type=OrderType.ASK)
        mm.submit_orders(symbol, [other_order])
        self.assertEqual(mm.lowest_ask[symbol].price, other_order.price)
        # order matters, since it determines execution order!
        self.assertEqual(mm.ask[symbol][order.price][0], order)
        self.assertEqual(mm.ask[symbol][order.price][1], other_order)

    def test_initial_unmatched_bids(self):
        order = self.given_order(order_type=OrderType.BID)
        symbol = order.symbol
        mm = self.given_market_maker()
        mm.submit_orders(symbol, [order])
        self.assertEqual(mm.highest_bid[symbol], order)
        self.assertEqual(mm.bid[order.symbol][order.price][0], order)

        # An equal bid won't update the high, yet gets registered for later matching
        other_order = self.given_order(order_type=OrderType.BID)
        mm.submit_orders(symbol, [other_order])
        self.assertEqual(mm.highest_bid[symbol].price, other_order.price)
        # order matters, since it determines execution order!
        self.assertEqual(mm.bid[symbol][order.price][0], order)
        self.assertEqual(mm.bid[symbol][order.price][1], other_order)

    def test_perfect_match(self):
        buyer, seller = uuid.uuid4(), uuid.uuid4()
        mm = self.given_market_maker()
        mm.register_participant(buyer, {'TSMC': 1000, 'CASH': 200_000})
        mm.register_participant(seller, {'TSMC': 1000, 'CASH': 200_000})

        sell = self.given_order(order_type=OrderType.ASK, other_party=seller)
        symbol = sell.symbol
        mm.submit_orders(symbol, [sell])

        buy = self.given_order(order_type=OrderType.BID, other_party=buyer)
        symbol = buy.symbol
        mm.submit_orders(symbol, [buy])
        self.assertEqual(mm.participants[buyer]['CASH'], 200_000 - sell.amount * sell.price)
        self.assertEqual(mm.participants[seller]['CASH'], 200_000 + sell.amount * sell.price)
        self.assertEqual(mm.participants[buyer]['TSMC'], 1000 + sell.amount)
        self.assertEqual(mm.participants[seller]['TSMC'], 1000 - sell.amount)

    def test_multi_match(self):
        buyer, seller1, seller2 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        mm = self.given_market_maker()
        mm.register_participant(buyer, {'TSMC': 1000, 'CASH': 200_000})
        mm.register_participant(seller1, {'TSMC': 1000, 'CASH': 200_000})
        mm.register_participant(seller2, {'TSMC': 8000, 'CASH': 200_000})

        sell0 = self.given_order(order_type=OrderType.ASK, other_party=seller1,
                                 price=140, amount=100)
        sell1 = self.given_order(order_type=OrderType.ASK, other_party=seller1,
                                 price=120, amount=100)
        sell2 = self.given_order(order_type=OrderType.ASK, other_party=seller1,
                                 price=100, amount=50)
        sell3 = self.given_order(order_type=OrderType.ASK, other_party=seller2,
                                 price=100, amount=60)
        symbol = sell1.symbol
        mm.submit_orders(symbol, [sell0, sell1, sell2, sell3])

        self.assertEqual(3, len(mm.ask[symbol]))

        buy = self.given_order(order_type=OrderType.BID, other_party=buyer,
                               price=130, amount=200)
        symbol = buy.symbol
        mm.submit_orders(symbol, [buy])

        # sell0 is unchanged
        # sell1 is gone, sell2 is gone, there are 50 more to buy
        # buyer has 23_000 Dollar off.

        pass
