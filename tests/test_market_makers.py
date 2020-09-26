import datetime as dt
import uuid
from copy import deepcopy
from unittest import TestCase

from markets.orders import OrderType, Order, ExecutionType
from markets.realistic import MarketMaker


class MarketMakerTest(TestCase):

    def setUp(self) -> None:
        self.order = Order(other_party=uuid.uuid4(), order_type=OrderType.ASK, execution_type=ExecutionType.LIMIT,
                           symbol='TSMC', amount=100, price=134, expiry=dt.datetime.now())
        self.symbols = {'TSMC': 100.0, 'NVDA': 200.0}

    def given_market_maker(self) -> MarketMaker:
        return MarketMaker(self.symbols)

    def given_order(self, **kwargs):
        order = deepcopy(self.order)
        for item in kwargs:
            order.__setattr__(item, kwargs[item])
        if order.execution_type == ExecutionType.MARKET:
            order.price = None
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
            mm.submit_orders([order])
            self.fail("Should have raised ValueError")
        except ValueError as ve:
            self.assertTrue("Illegal order" in str(ve))
        try:
            mm.submit_orders([order])
            self.fail("Should have raised ValueError")
        except ValueError as ve:
            self.assertTrue("Illegal order" in str(ve))

    def test_initial_ask_and_bid(self):
        for order_type in OrderType:
            order = self.given_order(order_type=order_type)
            symbol, price = order.symbol, order.price
            mm = self.given_market_maker()
            mm.submit_orders([order])
            self.assertEqual(mm.candidates[order_type][symbol], order)
            self.assertEqual(mm.orders[order_type][symbol][price][0], order)

            # An equal bid won't update the high, yet gets registered for later matching
            other_order = self.given_order(order_type=order_type)
            mm.submit_orders([other_order])
            self.assertEqual(mm.candidates[order_type][symbol].price, other_order.price)
            # order matters, since it determines execution order!
            self.assertEqual(mm.orders[order_type][symbol][price][0], order)
            self.assertEqual(mm.orders[order_type][symbol][price][1], other_order)

    def test_initial_unmatched_orders(self):

        for order_type in OrderType:
            order = self.given_order(order_type=order_type)
            symbol = order.symbol
            mm = self.given_market_maker()
            mm.submit_orders([order])
            self.assertEqual(mm.candidates[order_type][symbol], order)
            self.assertEqual(mm.orders[order_type][order.symbol][order.price][0], order)

            # An equal order won't replace the current candidate, yet gets registered for later matching
            other_order = self.given_order(order_type=order_type)
            mm.submit_orders([other_order])
            self.assertEqual(mm.candidates[order_type][symbol].price, other_order.price)
            # order matters, since it determines execution order!
            self.assertEqual(mm.orders[order_type][symbol][order.price][0], order)
            self.assertEqual(mm.orders[order_type][symbol][order.price][1], other_order)

    def test_perfect_match(self):
        symbol = 'TSMC'
        buyer, seller = uuid.uuid4(), uuid.uuid4()
        mm = self.given_market_maker()
        mm.register_participant(buyer, {symbol: 1000, 'CASH': 200_000})
        mm.register_participant(seller, {symbol: 1000, 'CASH': 200_000})

        sell = self.given_order(order_type=OrderType.ASK, other_party=seller)
        buy = self.given_order(order_type=OrderType.BID, other_party=buyer)

        # Whoever is first, we should have a perfect match
        for pair in [[buy, sell], [sell, buy]]:
            prev_buyer = deepcopy(mm.participants[buyer])
            prev_seller = deepcopy(mm.participants[seller])

            mm.submit_orders(pair)

            self.assertEqual(mm.participants[buyer]['CASH'], prev_buyer['CASH'] - sell.amount * sell.price)
            self.assertEqual(mm.participants[seller]['CASH'], prev_seller['CASH'] + sell.amount * sell.price)
            self.assertEqual(mm.participants[buyer][symbol], prev_buyer[symbol] + sell.amount)
            self.assertEqual(mm.participants[seller][symbol], prev_seller[symbol] - sell.amount)

    def test_multi_match_buy(self):
        buyer, seller1, seller2 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        mm = self.given_market_maker()
        mm.register_participant(buyer, {'TSMC': 1000, 'CASH': 200_000})
        mm.register_participant(seller1, {'TSMC': 1000, 'CASH': 200_000})
        mm.register_participant(seller2, {'TSMC': 1000, 'CASH': 200_000})

        sell0 = self.given_order(order_type=OrderType.ASK, other_party=seller1,
                                 price=140, amount=100)
        sell1 = self.given_order(order_type=OrderType.ASK, other_party=seller1,
                                 price=120, amount=100)
        sell2 = self.given_order(order_type=OrderType.ASK, other_party=seller1,
                                 price=100, amount=50)
        sell3 = self.given_order(order_type=OrderType.ASK, other_party=seller2,
                                 price=100, amount=60)
        symbol = sell1.symbol
        mm.submit_orders([sell0, sell1, sell2, sell3])

        self.assertEqual(3, len(mm.orders[OrderType.ASK][symbol]))

        buy = self.given_order(order_type=OrderType.BID, other_party=buyer,
                               price=130, amount=200)
        symbol = buy.symbol
        mm.submit_orders([buy])

        # seller2 sold her 60 shares for 100$ each
        self.assertEqual(mm.participants[seller2], {
            'TSMC': 1000 - 60,
            'CASH': 200_000 + 60 * 100})

        # seller1 sold 50 for 100 and 90 for 120
        self.assertEqual(mm.participants[seller1], {
            'TSMC': 1000 - 50 - 90,
            'CASH': 200_000 + 50 * 100 + 90 * 120})

        # buyer bought 110 for 100 and the remining 90 for 120
        self.assertEqual(mm.participants[buyer], {
            'TSMC': 1000 + 200,
            'CASH': 200_000 - 110 * 100 - 90 * 120})

        buy = self.given_order(order_type=OrderType.BID, other_party=buyer,
                               price=130, amount=50)
        mm.submit_orders([buy])

        # buyer bought another 10 for 120
        # buyer bought 110 for 100 and the remining 90 for 120
        self.assertEqual(mm.participants[buyer], {
            'TSMC': 1000 + 200 + 10,
            'CASH': 200_000 - 110 * 100 - 90 * 120 - 10 * 120})

        # buyer still bidding 130 for the remaining 30
        self.assertEqual(mm.orders[OrderType.BID][symbol][130][0].amount, 40)

    def test_multi_match_sell(self):
        seller, buyer1, buyer2 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        mm = self.given_market_maker()
        mm.register_participant(seller, {'TSMC': 1000, 'CASH': 200_000})
        mm.register_participant(buyer1, {'TSMC': 1000, 'CASH': 200_000})
        mm.register_participant(buyer2, {'TSMC': 1000, 'CASH': 200_000})

        buy0 = self.given_order(order_type=OrderType.BID, other_party=buyer1,
                                price=100, amount=100)
        buy1 = self.given_order(order_type=OrderType.BID, other_party=buyer1,
                                price=120, amount=100)
        buy2 = self.given_order(order_type=OrderType.BID, other_party=buyer1,
                                price=140, amount=50)
        buy3 = self.given_order(order_type=OrderType.BID, other_party=buyer2,
                                price=140, amount=60)

        symbol = 'TSMC'
        mm.submit_orders([buy3, buy2, buy1, buy0])

        self.assertEqual(3, len(mm.orders[OrderType.BID][symbol]))

        sell = self.given_order(order_type=OrderType.ASK, other_party=seller,
                                price=110, amount=200)

        mm.submit_orders([sell])

        # buyer2 bought her 60 shares for 140$ each
        self.assertEqual(mm.participants[buyer2], {
            'TSMC': 1000 + 60,
            'CASH': 200_000 - 60 * 110})

        # buyer1 bought 50 for 110 and 90 for 120
        self.assertEqual(mm.participants[buyer1], {
            'TSMC': 1000 + 50 + 90,
            'CASH': 200_000 - 50 * 110 - 90 * 110})

        # seller sold 110 for 140 and the remining 90 for 120
        self.assertEqual(mm.participants[seller], {
            'TSMC': 1000 - 200,
            'CASH': 200_000 + 110 * 110 + 90 * 110})

        sell = self.given_order(order_type=OrderType.ASK, other_party=seller,
                                price=110, amount=50)
        mm.submit_orders([sell])

        # seller sold another 10 for 110
        self.assertEqual(mm.participants[seller], {
            'TSMC': 1000 - 200 - 10,
            'CASH': 200_000 + 110 * 110 + 90 * 110 + 10 * 110})

        # seller still asking 110 for the remaining 40
        self.assertEqual(mm.orders[OrderType.ASK][symbol][110][0].amount, 40)

    def test_market_sell_order(self):
        buyer1, buyer2, seller1, seller2 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        mm = self.given_market_maker()
        mm.register_participant(buyer1, {'TSMC': 1000, 'NVDA': 1000, 'CASH': 200_000})
        mm.register_participant(buyer2, {'TSMC': 1000, 'NVDA': 1000, 'CASH': 200_000})
        mm.register_participant(seller1, {'TSMC': 1000, 'NVDA': 1000, 'CASH': 200_000})
        mm.register_participant(seller2, {'TSMC': 1000, 'NVDA': 1000, 'CASH': 200_000})

        sell_l = self.given_order(order_type=OrderType.ASK, other_party=seller1,
                                  amount=200, price=120)
        sell_m1 = self.given_order(order_type=OrderType.ASK, other_party=seller1,
                                   amount=40, execution_type=ExecutionType.MARKET)
        sell_m2 = self.given_order(order_type=OrderType.ASK, other_party=seller2,
                                   amount=70, execution_type=ExecutionType.MARKET)
        # this will find matching limit order
        buy1 = self.given_order(order_type=OrderType.BID, other_party=buyer1,
                                price=130, amount=50)

        # this will not find a matching limit order, so the queued market order will be executed
        buy2 = self.given_order(order_type=OrderType.BID, other_party=buyer2,
                                price=110, amount=60)

        mm.submit_orders([sell_m1, sell_m2, sell_l, buy1, buy2])

        # 1st tx: s1 -> b1 50 @ 120
        # 2nd tx: s1 -> b2 40 @ 110
        # 3rd tx: s2 -> b2 20 @ 110
        self.assertEqual(mm.participants[seller1], {
            'TSMC': 1000 - (40 + 50),
            'NVDA': 1000,
            'CASH': 200_000 + 40 * 110 + 50 * 120})
        self.assertEqual(mm.participants[seller2], {
            'TSMC': 1000 - 20,
            'NVDA': 1000,
            'CASH': 200_000 + 20 * 110})
        self.assertEqual(mm.participants[buyer1], {
            'TSMC': 1000 + 50,
            'NVDA': 1000,
            'CASH': 200_000 - 50 * 120})
        self.assertEqual(mm.participants[buyer2], {
            'TSMC': 1000 + (40 + 20),
            'NVDA': 1000,
            'CASH': 200_000 - (40 + 20) * 110})

    def test_market_buy_order(self):
        buyer1, buyer2, seller1, seller2 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        mm = self.given_market_maker()

        mm.register_participant(buyer1, {'TSMC': 1000, 'CASH': 200_000})
        mm.register_participant(buyer2, {'TSMC': 1000, 'CASH': 200_000})
        buy_l = self.given_order(order_type=OrderType.BID, other_party=buyer1,
                                 amount=200, price=120)
        buy_m1 = self.given_order(order_type=OrderType.BID, other_party=buyer1,
                                  amount=40, execution_type=ExecutionType.MARKET)
        buy_m2 = self.given_order(order_type=OrderType.BID, other_party=buyer2,
                                  amount=70, execution_type=ExecutionType.MARKET)

        mm.register_participant(seller1, {'TSMC': 1000, 'CASH': 200_000})
        # this will find a matching limit order
        sell1 = self.given_order(order_type=OrderType.ASK, other_party=seller1,
                                 amount=50, price=110)

        mm.register_participant(seller2, {'TSMC': 1000, 'CASH': 200_000})
        sell2 = self.given_order(order_type=OrderType.ASK, other_party=seller2,
                                 amount=100, price=130)

        mm.submit_orders([buy_l, buy_m1, buy_m2, sell1, sell2])

        # 1st tx: s1 -> b1 - 50 @ 110
        # 2nd tx: s2 -> b1 - 40 @ 130
        # 3rd tx: s2 -> b2 - 60 @ 130
        self.assertEqual(mm.participants[buyer1], {
            'TSMC': 1000 + 90,
            'CASH': 200_000 - 50 * 110 - 40 * 130
        })
        self.assertEqual(mm.participants[buyer2], {
            'TSMC': 1000 + 60,
            'CASH': 200_000 - 60 * 130
        })
        self.assertEqual(mm.participants[seller1], {
            'TSMC': 1000 - 50,
            'CASH': 200_000 + 50 * 110
        })
        self.assertEqual(mm.participants[seller2], {
            'TSMC': 1000 - 100,
            'CASH': 200_000 + (60 + 40) * 130
        })

    def test_large_market_order_shifts_price(self):

        buyer1, seller1, buyer2, seller2 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        mm = self.given_market_maker()
        mm.register_participant(buyer1, {'TSMC': 1000, 'CASH': 200_000})
        mm.register_participant(seller1, {'TSMC': 1000, 'CASH': 200_000})
        mm.register_participant(buyer2, {'TSMC': 1000, 'CASH': 200_000})
        mm.register_participant(seller2, {'TSMC': 1000, 'CASH': 200_000})

        buys = [self.given_order(order_type=OrderType.BID, other_party=buyer1,
                                 amount=50, price=100 + inc) for inc in range(10)]

        sell_m = self.given_order(order_type=OrderType.ASK, other_party=seller1,
                                  amount=300, execution_type=ExecutionType.MARKET)

        mm.submit_orders(buys + [sell_m])

        sells = [self.given_order(order_type=OrderType.ASK, other_party=seller2,
                                  amount=50, price=110 + inc) for inc in range(10)]

        buy_m = self.given_order(order_type=OrderType.BID, other_party=buyer2,
                                 amount=300, execution_type=ExecutionType.MARKET)

        amount_1 = 50 * (109 + 108 + 107 + 106 + 105 + 104)
        self.assertEqual(mm.participants[buyer1], {
            'TSMC': 1300,
            'CASH': 200_000 - amount_1
        })

        self.assertEqual(mm.participants[seller1], {
            'TSMC': 700,
            'CASH': 200_000 + amount_1
        })

        self.assertEqual(104, mm.mrtxp['TSMC'])

        mm.submit_orders(sells + [buy_m])

        amount_2 = 50 * (110 + 111 + 112 + 113 + 114 + 115)
        self.assertEqual(mm.participants[buyer2], {
            'TSMC': 1300,
            'CASH': 200_000 - amount_2
        })

        self.assertEqual(mm.participants[seller2], {
            'TSMC': 700,
            'CASH': 200_000 + amount_2
        })

        self.assertEqual(115, mm.mrtxp['TSMC'])

        prices = mm.get_prices()

        self.assertEqual(prices['TSMC'], {'bid': 103, 'ask': 116, 'last': 115})
