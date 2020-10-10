import logging
from collections import OrderedDict
from copy import deepcopy
from typing import Optional, Dict, List, Tuple, Union

from .Clock import Clock
from .abstract import AbstractMarket, AbstractMarketMaker, AbstractInvestor
from .Order import Order, OrderType, ExecutionType
from .Stock import Stock


class MarketMaker(AbstractMarketMaker):
    """
    Matching Algorithm:
    Matching takes place at order entry.
    The clearing price is always the matching ask price.
    For ask orders: The matching bid is the most recent of the highest bids recorded earlier.
    For bid orders: The matching bid is the most recent of the lowest asks recorded earlier.
    If no match is found or the order cannot be executed fully, the remaining order is queued.
    Since market orders will almost certainly be executed immediately, they will hardly ever be queued.
    However, should that happen, here are the rules.
    Queued market orders are only executed if there is no matching limit order. Execution takes place at the
    ask order's price, if it's a limit order. If the ask order is a market order,
    the most recent clearing price is used.
    """

    def __init__(self, market: AbstractMarket):
        """
        :param market: a market instance
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        stocks: List[Stock] = market.get_stocks()

        self.symbols = [stock.name for stock in stocks]
        self.mrtxp = {stock.name: round(stock.psi(0), 2) for stock in stocks}

        # like {uuid: {'portfolio': {'TSLA': 1200}, 'contact': AbstractInvestor}
        self.participants: Dict[str, Dict[str, Union[AbstractInvestor, Dict[str, float]]]] = {}

        self.orders: Dict[OrderType, Dict[str, OrderedDict]] = {}
        self.market_orders: Dict[OrderType, Dict[str, List[Order]]] = {}
        for order_type in OrderType:
            self.orders[order_type] = {}
            self.market_orders[order_type] = {}
            for stock in stocks:
                self.orders[order_type][stock.name] = OrderedDict()
                self.market_orders[order_type][stock.name] = []

        self.candidates = {
            OrderType.BID: {symbol: None for symbol in self.symbols},  # highest bid
            OrderType.ASK: {symbol: None for symbol in self.symbols}  # lowest ask
        }
        self.logger.info(f"Starting up. OSID {self.osid()} may not reflect actual host process yet.")

    def __repr__(self):
        return f'MarketMaker {self.osid()}'

    def get_prices(self) -> Dict[str, Dict[str, float]]:
        return {
            symbol: {'bid': self.get_candidate_price(OrderType.BID, symbol),
                     'ask': self.get_candidate_price(OrderType.ASK, symbol),
                     'last': self.mrtxp[symbol]}
            for symbol in self.symbols
        }

    def get_order_book(self) -> Dict[str, Dict[float, Tuple[str, float]]]:
        order_book = {}
        for symbol in self.symbols:
            chapter = {}
            for order_type in self.orders:
                if self.orders[order_type].get(symbol):
                    for price, orders in self.orders[order_type][symbol].items():
                        chapter[price] = (sum([order.amount for order in orders]),
                                          order_type.value[0])
            order_book[symbol] = chapter
        return order_book

    def get_candidate_price(self, order_type: OrderType, symbol: str):
        candidate = self.candidates[order_type].get(symbol)
        return candidate.price if candidate else None

    def register_participant(self, investor: AbstractInvestor):
        portfolio = investor.get_portfolio()
        if not all([key in self.symbols for key in portfolio.keys() if key != 'CASH']):
            self.logger.error(f"Can't register {investor.get_qname()}: Not all given assets are supported here.")
            raise ValueError("Illegal portfolio: Not all given assets are supported here.")
        self.participants[investor.get_qname()] = {'portfolio': portfolio, 'contact': investor}
        self.logger.info(f"Registered participant {investor.get_qname()}")

    def submit_orders(self, orders: List[Order], clock: Clock):
        self.logger.debug(f"[{str(clock)}]: Received {len(orders)} order" + ("s" if len(orders) != 1 else ""))
        for order in orders:
            symbol = order.symbol
            if symbol not in self.symbols:
                raise ValueError(f"Illegal order: symbol {symbol} not traded here.")

            order = deepcopy(order)
            candidate = self.find_candidate(order, clock)
            if candidate is None:
                if order.expires_at <= clock.seconds:
                    self.participants[order.other_party]['contact'].report_expiry(order)
                else:
                    self.register_order(order)
            else:
                self.process_order(order, candidate, clock)

    def find_candidate(self, order: Order, clock: Clock) -> Optional[Order]:
        candidate = self.candidates[order.order_type.other()].get(order.symbol)
        if candidate and candidate.expires_at >= clock.seconds:
            return candidate
        elif candidate:  # There is a candidate, but it's expired
            self.remove_order(candidate)
            return self.replace_candidate_if_possible(candidate, clock)
        else:
            return None

    def remove_expired_orders(self, clock: Clock):
        self.logger.warning(f'[{str(clock)}] Would Remove expired orders, but that is not implemented yet.')
        pass

    def register_order(self, order: Order):
        order_type, symbol, price = order.order_type, order.symbol, order.price

        # set highest/lowest, if appropriate
        if not self.candidates[order_type].get(symbol) or order.precedes(self.candidates[order_type][symbol]):
            self.candidates[order_type][symbol] = order

        # append to the list of same type - same price orders
        if order.execution_type == ExecutionType.LIMIT:
            queue = self.orders[order_type][symbol]
            if queue.get(price) is None:
                queue[price] = []

            queue[price].append(order)
        else:
            # market orders are queued separately
            self.market_orders[order_type][symbol].append(order)

    def process_order(self, order: Order, candidate: Order, clock: Clock):
        done = False
        while not done:
            order, done = self.process_order_maybe_partially(order, candidate, clock)
            if not done:
                candidate = self.candidates[order.order_type.other()].get(order.symbol)
                if not candidate:
                    break

    def determine_price(self, bid: Order, ask: Order) -> float:
        if ask.execution_type == ExecutionType.LIMIT:
            return ask.price
        elif bid.execution_type == ExecutionType.LIMIT:
            return min(bid.price, self.get_prices()[ask.symbol]['last'])
        else:
            return self.mrtxp[ask.symbol]

    def execute_trade(self, bid: Order, ask: Order, clock: Clock):

        tx_price = self.determine_price(bid, ask)
        tx_volume = min(ask.amount, bid.amount)
        bid.amount -= tx_volume
        ask.amount -= tx_volume
        self.logger.debug(f'Executing trade: {tx_volume} shares of {bid.symbol} for ${tx_price}')
        self.execute_transaction(buyer=bid.other_party,
                                 seller=ask.other_party,
                                 symbol=bid.symbol,
                                 volume=tx_volume,
                                 price=tx_price,
                                 clock=clock)
        self.mrtxp[bid.symbol] = tx_price

    def replace_candidate_if_possible(self, candidate: Order, clock: Clock) -> Optional[Order]:
        symbol = candidate.symbol
        order_type = candidate.order_type
        if candidate.execution_type == ExecutionType.LIMIT:
            # next candidate price is popped from top (lowest_ask) or bottom (highest_bid)
            prices = sorted(list(self.orders[order_type][symbol].keys()))
            if len(prices) > 0:
                pop_index = 0 if order_type == OrderType.ASK else -1
                new_price = prices[pop_index]

                # pick the least recent order of that price as new candidate
                new_candidate = self.orders[order_type][symbol][new_price][0]
                if new_candidate.expires_at >= clock.seconds:
                    self.candidates[candidate.order_type][symbol] = new_candidate
                else:
                    del self.orders[order_type][symbol][new_price][0]
                    if len(self.orders[order_type][symbol][new_price]) == 0:
                        del self.orders[order_type][symbol][new_price]
                    return None
            else:
                new_candidate = None
                self.candidates[candidate.order_type][symbol] = None

            return new_candidate
        else:
            potentials = self.market_orders[order_type][symbol]
            if len(potentials) > 0:
                new_candidate = potentials[0]  # The least resently registered order
                self.candidates[candidate.order_type][symbol] = new_candidate
                return new_candidate
            else:
                self.candidates[candidate.order_type][symbol] = None
                return None

    def find_market_candidate(self, order_type: OrderType, symbol: str) -> Optional[Order]:
        market_candidates = self.market_orders[order_type][symbol]
        if market_candidates and len(market_candidates) > 0:
            return market_candidates[0]
        return None

    def process_order_maybe_partially(self, order: Order, candidate: Order,
                                      clock: Clock) -> Tuple[Optional[Order], bool]:

        bid, ask = Order.as_bid_ask(order, candidate)
        if ask.matches(bid):
            self.execute_trade(bid, ask, clock)
        else:
            candidate = self.find_market_candidate(candidate.order_type, ask.symbol)
            if candidate:
                bid, ask = Order.as_bid_ask(order, candidate)
                self.execute_trade(bid, ask, clock)
            else:
                self.register_order(order)
                return None, True

        if candidate and candidate.amount == 0:
            self.remove_order(candidate)
            self.replace_candidate_if_possible(candidate, clock)

        if order.amount == 0:
            return None, True
        else:
            return order, False

    def remove_order(self, order):
        symbol, order_type, price = order.symbol, order.order_type, order.price
        if order.execution_type == ExecutionType.LIMIT:
            del self.orders[order_type][symbol][price][0]
            if len(self.orders[order_type][symbol][price]) == 0:
                del self.orders[order_type][symbol][price]
        else:
            del self.market_orders[order_type][symbol][0]
            if len(self.market_orders[order_type][symbol]) == 0:
                del self.orders[order_type][symbol]

    def execute_transaction(self, buyer, seller, symbol, volume, price, clock):

        self.participants[buyer]['portfolio'][symbol] += volume
        self.participants[seller]['portfolio'][symbol] -= volume

        self.participants[buyer]['portfolio']['CASH'] -= volume * price
        self.participants[seller]['portfolio']['CASH'] += volume * price

        # TODO: Better have the tests supply some dummy thing here and always demand that contacts are available
        buyer_ref = self.participants[buyer]['contact']
        if buyer_ref:
            self.logger.debug(f'Reporting buy to {buyer_ref.get_qname()}')
            buyer_ref.report_tx(OrderType.BID, symbol, volume, price, volume * price, clock)

        seller_ref = self.participants[seller]['contact']
        if seller_ref:
            self.logger.debug(f'Reporting sell to {seller_ref.get_qname()}')
            seller_ref.report_tx(OrderType.ASK, symbol, volume, price, volume * price, clock)

    def trades_in(self, stock: str) -> bool:
        return stock in self.symbols

    def osid(self) -> str:
        import os
        return f'({os.getpid()}-{id(self)})'
