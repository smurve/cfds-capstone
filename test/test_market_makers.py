from copy import deepcopy
from typing import List, Dict, Any
from unittest import TestCase
from unittest.mock import Mock

from markets.realistic import (Order, OrderType, ExecutionType, Clock,
                               MarketMaker, USITMarket, ChartInvestor, AbstractInvestor)
from markets.realistic.strategy import PriceValueStrategyFactory

ASK = OrderType.ASK
BID = OrderType.BID
LIMIT = ExecutionType.LIMIT
MARKET = ExecutionType.MARKET
TSMC = 'TSMC'
AAPL = 'AAPL'

BUYER1 = 'buyer1'
BUYER2 = 'buyer2'
SELLER1 = 'seller1'
SELLER2 = 'seller2'


class MarketMakerTest(TestCase):

    def setUp(self) -> None:
        self.order = Order("anybody", order_type=ASK,
                           execution_type=LIMIT,
                           symbol='TSMC', amount=100, price=134, expires_at=10)
        self.symbols = {'TSMC': 100.0, 'NVDA': 200.0}

        self.market = USITMarket({'TSMC': 100., 'NVDA': 200.}, noise=0.)

        self.strategy_factory = PriceValueStrategyFactory(action_threshold=0.01)

    def given_market_maker(self) -> MarketMaker:
        initial_prices = {stock.name: round(stock.psi(0), 2) for stock in self.market.get_stocks()}
        return MarketMaker(initial_prices)

    def given_order(self, **kwargs):
        order = deepcopy(self.order)
        for item in kwargs:
            order.__setattr__(item, kwargs[item])
        if order.execution_type == ExecutionType.MARKET:
            order.price = None
        if not isinstance(order.other_party, str):
            order.other_party = str(order.other_party)
        if order.expires_at is None:
            order.expires_at = 1000  # that means never in the context of this test
        return order

    def given_investor(self, symbol: str) -> AbstractInvestor:
        return ChartInvestor(market=self.market,
                             name='Michael Burry',
                             portfolio={symbol: 1000},
                             cash=200_000,
                             strategy_factory=self.strategy_factory)

    def test_matching_scenario(self):

        sell = Order(SELLER1, ASK, LIMIT, TSMC, 100, 135., 300)
        clock = Clock(initial_seconds=120)
        # top limit candidate matches, but is expired
        top_l_exp = Order(BUYER1, BID, LIMIT, TSMC, 100, 136., 60)
        # next limit candidate no match
        next_l_no_match = Order(BUYER1, BID, LIMIT, TSMC, 100, 134., 300)
        # top market candidate epired
        top_m_exp = Order(BUYER1, BID, MARKET, TSMC, 100, -1., 60)
        # next market candidate good
        next_m_good = Order(BUYER1, BID, MARKET, TSMC, 200, -1, 300)

        mm = self.given_market_maker()
        buyer = Mock(spec=AbstractInvestor)
        buyer.get_portfolio.return_value = {TSMC: 1000, 'CASH': 200_000}
        buyer.get_qname.return_value = BUYER1
        mm.register_participant(buyer)
        seller = Mock(spec=AbstractInvestor)
        seller.get_portfolio.return_value = {TSMC: 1000, 'CASH': 200_000}
        seller.get_qname.return_value = SELLER1
        mm.register_participant(seller)

        mm.submit_orders([top_l_exp, next_l_no_match, top_m_exp, next_m_good], clock)

        mm.submit_orders([sell], clock)

        self.then_these_orders_are_still_in_the_books(mm, next_l_no_match)
        self.then_market_candidates_should_contain(mm, Order(BUYER1, BID, MARKET, TSMC, 100, 0, 300))
        self.then_limit_candidates_should_contain(mm, next_l_no_match)
        self.then_transaction_should_have_been_executed([{
            'symbol': 'TSMC',
            'volume': 100,
            'price': 135.0,
            'buyer': buyer,
            'seller': seller,
            'clock': clock}])

    def then_these_orders_are_still_in_the_books(self, mm: MarketMaker, *orders):
        for order in orders:
            self.assertTrue(order in mm.market_orders[order.order_type][order.symbol] or
                            order in mm.orders[order.order_type][order.symbol][order.price])

    def then_market_candidates_should_contain(self, mm: MarketMaker, *orders):
        for order in orders:
            self.assertTrue(any([order.equivalent(candidate)
                                 for candidate in mm.market_orders[order.order_type][order.symbol]]))

    def then_limit_candidates_should_contain(self, mm: MarketMaker, *orders):
        for order in orders:
            candidate = mm.candidates[BID][order.symbol]
            self.assertTrue(order.equivalent(candidate))

    @staticmethod
    def then_transaction_should_have_been_executed(transactions: List[Dict[str, Any]]):
        for tx in transactions:
            tx['buyer'].report_tx.assert_called_once_with(BID, tx['symbol'], tx['volume'], tx['price'],
                                                          tx['volume'] * tx['price'], tx['clock'])
            tx['seller'].report_tx.assert_called_once_with(ASK, tx['symbol'], tx['volume'], tx['price'],
                                                           tx['volume'] * tx['price'], tx['clock'])

    def test_register_participant_with_unknown_symbol(self):
        unknown_symbol = 'AAPL'
        mm = self.given_market_maker()
        inv = self.given_investor(unknown_symbol)
        try:
            mm.register_participant(inv)
            self.fail("Should have raised ValueError")
        except ValueError as ve:
            self.assertTrue("Illegal portfolio" in str(ve))

    def test_initial_ask_and_bid(self):
        for order_type in OrderType:
            order = self.given_order(order_type=order_type)
            symbol, price = order.symbol, order.price
            mm = self.given_market_maker()
            mm.submit_orders([order], Clock())
            self.assertEqual(mm.candidates[order_type][symbol], order)
            self.assertEqual(mm.orders[order_type][symbol][price][0], order)

            # An equal bid won't update the high, yet gets registered for later matching
            other_order = self.given_order(order_type=order_type)
            mm.submit_orders([other_order], Clock())
            self.assertEqual(mm.candidates[order_type][symbol].price, other_order.price)
            # order matters, since it determines execution order!
            self.assertEqual(mm.orders[order_type][symbol][price][0], order)
            self.assertEqual(mm.orders[order_type][symbol][price][1], other_order)

    def test_initial_unmatched_orders(self):

        for order_type in OrderType:
            order = self.given_order(order_type=order_type)
            symbol = order.symbol
            mm = self.given_market_maker()
            mm.submit_orders([order], Clock())
            self.assertEqual(mm.candidates[order_type][symbol], order)
            self.assertEqual(mm.orders[order_type][order.symbol][order.price][0], order)

            # An equal order won't replace the current candidate, yet gets registered for later matching
            other_order = self.given_order(order_type=order_type)
            mm.submit_orders([other_order], Clock())
            self.assertEqual(mm.candidates[order_type][symbol].price, other_order.price)
            # order matters, since it determines execution order!
            self.assertEqual(mm.orders[order_type][symbol][order.price][0], order)
            self.assertEqual(mm.orders[order_type][symbol][order.price][1], other_order)

    def test_perfect_match(self):
        symbol = 'TSMC'
        buyer, seller = self.given_investor(symbol), self.given_investor(symbol)
        mm = self.given_market_maker()
        mm.register_participant(buyer)
        mm.register_participant(seller)

        sell = self.given_order(order_type=OrderType.ASK, other_party=str(seller))
        buy = self.given_order(order_type=OrderType.BID, other_party=str(buyer))

        # Whoever is first, we should have a perfect match
        for pair in [[buy, sell], [sell, buy]]:
            prev_buyer = deepcopy(mm.participants[str(buyer)])
            prev_seller = deepcopy(mm.participants[str(seller)])

            mm.submit_orders(pair, Clock())

            self.assertEqual(mm.participants[str(buyer)]['portfolio']['CASH'],
                             prev_buyer['portfolio']['CASH'] - sell.amount * sell.price)
            self.assertEqual(mm.participants[str(seller)]['portfolio']['CASH'],
                             prev_seller['portfolio']['CASH'] + sell.amount * sell.price)
            self.assertEqual(mm.participants[str(buyer)]['portfolio'][symbol],
                             prev_buyer['portfolio'][symbol] + sell.amount)
            self.assertEqual(mm.participants[str(seller)]['portfolio'][symbol],
                             prev_seller['portfolio'][symbol] - sell.amount)

    def test_multi_match_buy(self):
        buyer, seller1, seller2 = [self.given_investor('TSMC') for _ in range(3)]
        mm = self.given_market_maker()
        mm.register_participant(buyer)
        mm.register_participant(seller1)
        mm.register_participant(seller2)

        sell0 = self.given_order(order_type=OrderType.ASK, other_party=seller1,
                                 price=140, amount=100)
        sell1 = self.given_order(order_type=OrderType.ASK, other_party=seller1,
                                 price=120, amount=100)
        sell2 = self.given_order(order_type=OrderType.ASK, other_party=seller1,
                                 price=100, amount=50)
        sell3 = self.given_order(order_type=OrderType.ASK, other_party=seller2,
                                 price=100, amount=60)
        symbol = sell1.symbol
        mm.submit_orders([sell0, sell1, sell2, sell3], Clock())

        self.assertEqual(3, len(mm.orders[OrderType.ASK][symbol]))

        buy = self.given_order(order_type=OrderType.BID, other_party=buyer,
                               price=130, amount=200)
        symbol = buy.symbol
        mm.submit_orders([buy], Clock())

        # seller2 sold her 60 shares for 100$ each
        self.assertEqual(mm.participants[str(seller2)]['portfolio'], {
            'TSMC': 1000 - 60,
            'CASH': 200_000 + 60 * 100})

        # seller1 sold 50 for 100 and 90 for 120
        self.assertEqual(mm.participants[str(seller1)]['portfolio'], {
            'TSMC': 1000 - 50 - 90,
            'CASH': 200_000 + 50 * 100 + 90 * 120})

        # buyer bought 110 for 100 and the remining 90 for 120
        self.assertEqual(mm.participants[str(buyer)]['portfolio'], {
            'TSMC': 1000 + 200,
            'CASH': 200_000 - 110 * 100 - 90 * 120})

        buy = self.given_order(order_type=OrderType.BID, other_party=buyer,
                               price=130, amount=50)
        mm.submit_orders([buy], Clock())

        # buyer bought another 10 for 120
        # buyer bought 110 for 100 and the remining 90 for 120
        self.assertEqual(mm.participants[str(buyer)]['portfolio'], {
            'TSMC': 1000 + 200 + 10,
            'CASH': 200_000 - 110 * 100 - 90 * 120 - 10 * 120})

        # buyer still bidding 130 for the remaining 30
        self.assertEqual(mm.orders[OrderType.BID][symbol][130][0].amount, 40)

    def test_multi_match_sell(self):
        seller, buyer1, buyer2 = [self.given_investor('TSMC') for _ in range(3)]
        mm = self.given_market_maker()
        mm.register_participant(seller)
        mm.register_participant(buyer1)
        mm.register_participant(buyer2)

        buy0 = self.given_order(order_type=OrderType.BID, other_party=buyer1,
                                price=100, amount=100)
        buy1 = self.given_order(order_type=OrderType.BID, other_party=buyer1,
                                price=120, amount=100)
        buy2 = self.given_order(order_type=OrderType.BID, other_party=buyer1,
                                price=140, amount=50)
        buy3 = self.given_order(order_type=OrderType.BID, other_party=buyer2,
                                price=140, amount=60)

        symbol = 'TSMC'
        mm.submit_orders([buy3, buy2, buy1, buy0], Clock())

        self.assertEqual(3, len(mm.orders[OrderType.BID][symbol]))

        sell = self.given_order(order_type=OrderType.ASK, other_party=seller,
                                price=110, amount=200)

        mm.submit_orders([sell], Clock())

        # buyer2 bought her 60 shares for 140$ each
        self.assertEqual(mm.participants[str(buyer2)]['portfolio'], {
            'TSMC': 1000 + 60,
            'CASH': 200_000 - 60 * 110})

        # buyer1 bought 50 for 110 and 90 for 120
        self.assertEqual(mm.participants[str(buyer1)]['portfolio'], {
            'TSMC': 1000 + 50 + 90,
            'CASH': 200_000 - 50 * 110 - 90 * 110})

        # seller sold 110 for 140 and the remining 90 for 120
        self.assertEqual(mm.participants[str(seller)]['portfolio'], {
            'TSMC': 1000 - 200,
            'CASH': 200_000 + 110 * 110 + 90 * 110})

        sell = self.given_order(order_type=OrderType.ASK, other_party=seller,
                                price=110, amount=50)
        mm.submit_orders([sell], Clock())

        # seller sold another 10 for 110
        self.assertEqual(mm.participants[str(seller)]['portfolio'], {
            'TSMC': 1000 - 200 - 10,
            'CASH': 200_000 + 110 * 110 + 90 * 110 + 10 * 110})

        # seller still asking 110 for the remaining 40
        self.assertEqual(mm.orders[OrderType.ASK][symbol][110][0].amount, 40)

    def test_market_sell_order(self):
        buyer1, buyer2, seller1, seller2 = [self.given_investor('TSMC') for _ in range(4)]
        mm = self.given_market_maker()
        mm.register_participant(buyer1)
        mm.register_participant(buyer2)
        mm.register_participant(seller1)
        mm.register_participant(seller2)

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

        mm.submit_orders([sell_m1, sell_m2, sell_l, buy1, buy2], Clock())

        # 1st tx: s1 -> b1 50 @ 120
        # 2nd tx: s1 -> b2 40 @ 110
        # 3rd tx: s2 -> b2 20 @ 110
        self.assertEqual(mm.participants[str(seller1)]['portfolio'], {
            'TSMC': 1000 - (40 + 50),
            'CASH': 200_000 + 40 * 110 + 50 * 120})
        self.assertEqual(mm.participants[str(seller2)]['portfolio'], {
            'TSMC': 1000 - 20,
            'CASH': 200_000 + 20 * 110})
        self.assertEqual(mm.participants[str(buyer1)]['portfolio'], {
            'TSMC': 1000 + 50,
            'CASH': 200_000 - 50 * 120})
        self.assertEqual(mm.participants[str(buyer2)]['portfolio'], {
            'TSMC': 1000 + (40 + 20),
            'CASH': 200_000 - (40 + 20) * 110})

    def test_market_buy_order(self):
        buyer1, buyer2, seller1, seller2 = [self.given_investor('TSMC') for _ in range(4)]
        mm = self.given_market_maker()

        mm.register_participant(buyer1)
        mm.register_participant(buyer2)
        buy_l = self.given_order(order_type=OrderType.BID, other_party=buyer1,
                                 amount=200, price=120)
        buy_m1 = self.given_order(order_type=OrderType.BID, other_party=buyer1,
                                  amount=40, execution_type=ExecutionType.MARKET)
        buy_m2 = self.given_order(order_type=OrderType.BID, other_party=buyer2,
                                  amount=70, execution_type=ExecutionType.MARKET)

        mm.register_participant(seller1)
        # this will find a matching limit order
        sell1 = self.given_order(order_type=OrderType.ASK, other_party=seller1,
                                 amount=50, price=110)

        mm.register_participant(seller2)
        sell2 = self.given_order(order_type=OrderType.ASK, other_party=seller2,
                                 amount=100, price=130)

        mm.submit_orders([buy_l, buy_m1, buy_m2, sell1, sell2], Clock())

        # 1st tx: s1 -> b1 - 50 @ 110
        # 2nd tx: s2 -> b1 - 40 @ 130
        # 3rd tx: s2 -> b2 - 60 @ 130
        self.assertEqual(mm.participants[str(buyer1)]['portfolio'], {
            'TSMC': 1000 + 90,
            'CASH': 200_000 - 50 * 110 - 40 * 130
        })
        self.assertEqual(mm.participants[str(buyer2)]['portfolio'], {
            'TSMC': 1000 + 60,
            'CASH': 200_000 - 60 * 130
        })
        self.assertEqual(mm.participants[str(seller1)]['portfolio'], {
            'TSMC': 1000 - 50,
            'CASH': 200_000 + 50 * 110
        })
        self.assertEqual(mm.participants[str(seller2)]['portfolio'], {
            'TSMC': 1000 - 100,
            'CASH': 200_000 + (60 + 40) * 130
        })

    def test_large_market_order_shifts_price(self):

        buyer1, seller1, buyer2, seller2 = [self.given_investor('TSMC') for _ in range(4)]
        mm = self.given_market_maker()
        mm.register_participant(buyer1)
        mm.register_participant(seller1)
        mm.register_participant(buyer2)
        mm.register_participant(seller2)

        buys = [self.given_order(order_type=OrderType.BID, other_party=buyer1,
                                 amount=50, price=100 + inc) for inc in range(10)]

        sell_m = self.given_order(order_type=OrderType.ASK, other_party=seller1,
                                  amount=300, execution_type=ExecutionType.MARKET)

        mm.submit_orders(buys + [sell_m], Clock())

        current_price = mm.get_prices()['TSMC']['last']
        amount_1 = 50 * 6 * current_price  # All for the current price
        self.assertEqual(mm.participants[str(buyer1)]['portfolio'], {
            'TSMC': 1300,
            'CASH': 200_000 - amount_1
        })

        self.assertEqual(mm.participants[str(seller1)]['portfolio'], {
            'TSMC': 700,
            'CASH': 200_000 + amount_1
        })

        self.assertEqual(101.0, mm.mrtxp['TSMC'])

        sells = [self.given_order(order_type=OrderType.ASK, other_party=seller2,
                                  amount=50, price=110 + inc) for inc in range(10)]

        buy_m = self.given_order(order_type=OrderType.BID, other_party=buyer2,
                                 amount=300, execution_type=ExecutionType.MARKET)

        mm.submit_orders(sells + [buy_m], Clock())

        amount_2 = 50 * (110 + 111 + 112 + 113 + 114 + 115)
        self.assertEqual(mm.participants[str(buyer2)]['portfolio'], {
            'TSMC': 1300,
            'CASH': 200_000 - amount_2
        })

        self.assertEqual(mm.participants[str(seller2)]['portfolio'], {
            'TSMC': 700,
            'CASH': 200_000 + amount_2
        })

        self.assertEqual(115, mm.mrtxp['TSMC'])

        prices = mm.get_prices()

        self.assertEqual(prices['TSMC'], {'bid': None, 'ask': None, 'last': 115})
