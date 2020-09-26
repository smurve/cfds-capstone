from collections import OrderedDict
from typing import Optional, Dict, List, Tuple
from uuid import UUID
from copy import deepcopy

from markets.abstract import AbstractMarketMaker
from markets.orders import Order, OrderType, ExecutionType


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

    def __init__(self, initial_prices: Dict[str, float]):
        """
        :param initial_prices: map of symbols with initial prices
        """
        self.symbols = list(initial_prices.keys())
        self.mrtxp = initial_prices

        self.participants: Dict[UUID, Dict[str, float]] = {}

        self.orders: Dict[OrderType, Dict[str, OrderedDict]] = {}
        self.market_orders: Dict[OrderType, Dict[str, List[Order]]] = {}
        for order_type in OrderType:
            self.orders[order_type] = {}
            self.market_orders[order_type] = {}
            for symbol in initial_prices:
                self.orders[order_type][symbol] = OrderedDict()
                self.market_orders[order_type][symbol] = []

        self.candidates = {
            OrderType.BID: {symbol: None for symbol in initial_prices},  # highest bid
            OrderType.ASK: {symbol: None for symbol in initial_prices}  # lowest ask
        }

    def get_prices(self) -> Dict[str, Dict[str, float]]:
        return {
            symbol: {'bid': self.get_candidate_price(OrderType.BID, symbol),
                     'ask': self.get_candidate_price(OrderType.ASK, symbol),
                     'last': self.mrtxp[symbol]}
            for symbol in self.symbols
        }

    def get_candidate_price(self, order_type: OrderType, symbol: str):
        candidate = self.candidates[order_type].get(symbol)
        return candidate.price if candidate else None

    def register_participant(self, uuid: UUID, portfolio: Dict[str, float]):
        if not all([key in self.symbols for key in portfolio.keys() if key != 'CASH']):
            raise ValueError("Illegal portfolio: Not all given assets are supported here.")
        self.participants[uuid] = portfolio

    def submit_orders(self, orders: List[Order]):
        for order in orders:
            symbol = order.symbol
            if symbol not in self.symbols:
                raise ValueError(f"Illegal order: symbol {symbol} no traded here.")

            order = deepcopy(order)
            candidate = self.candidates[order.order_type.other()].get(symbol)
            if candidate is None:
                self.register_order(order)
            else:
                self.process_order(order, candidate)

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
            # market order are queued separately
            self.market_orders[order_type][symbol].append(order)

    def process_order(self, order: Order, candidate: Order):
        done = False
        while not done:
            order, done = self.process_order_maybe_partially(order, candidate)
            if not done:
                candidate = self.candidates[order.order_type.other()].get(order.symbol)

    def determine_price(self, bid: Order, ask: Order) -> float:
        if ask.execution_type == ExecutionType.LIMIT:
            return ask.price
        elif bid.execution_type == ExecutionType.LIMIT:
            return bid.price
        else:
            return self.mrtxp[ask.symbol]

    def execute_trade(self, bid: Order, ask: Order):

        tx_price = self.determine_price(bid, ask)
        tx_volume = min(ask.amount, bid.amount)
        bid.amount -= tx_volume
        ask.amount -= tx_volume
        self.execute_transaction(buyer=bid.other_party,
                                 seller=ask.other_party,
                                 symbol=bid.symbol,
                                 volume=tx_volume,
                                 price=tx_price)
        self.mrtxp[bid.symbol] = tx_price

    def replace_candidate_if_possible(self, candidate: Order):
        self.remove_order(candidate)
        symbol = candidate.symbol
        # next candidate price is popped from top (lowest_ask) or bottom (highest_bid)
        order_type = candidate.order_type
        prices = sorted(list(self.orders[order_type][symbol].keys()))
        if len(prices) > 0:
            pop_index = 0 if order_type == OrderType.ASK else -1
            new_price = prices[pop_index]

            # pick the least recent order of that price as new candidate
            self.candidates[candidate.order_type][symbol] = self.orders[order_type][symbol][new_price][0]
        else:
            self.candidates[candidate.order_type][symbol] = None

    def find_market_candidate(self, order_type: OrderType, symbol: str) -> Optional[Order]:
        market_candidates = self.market_orders[order_type][symbol]
        if market_candidates and len(market_candidates) > 0:
            return market_candidates[0]
        return None

    def process_order_maybe_partially(self, order: Order, candidate: Order) -> Tuple[Optional[Order], bool]:

        bid, ask = Order.as_bid_ask(order, candidate)
        if ask.matches(bid):
            self.execute_trade(bid, ask)
        else:
            candidate = self.find_market_candidate(candidate.order_type, ask.symbol)
            if candidate:
                self.execute_trade(*Order.as_bid_ask(order, candidate))
            else:
                self.register_order(order)
                return None, True

        if candidate and candidate.amount == 0:
            if candidate.execution_type == ExecutionType.LIMIT:
                self.replace_candidate_if_possible(candidate)
            else:
                self.remove_order(candidate)

        if order.amount == 0:
            return None, True
        else:
            return order, False

    def remove_order(self, order):
        symbol, order_type, price = order.symbol, order.order_type, order.price
        if order.execution_type == ExecutionType.LIMIT:
            del self.orders[order_type][symbol][order.price][0]
            if len(self.orders[order_type][symbol][price]) == 0:
                del self.orders[order_type][symbol][order.price]
        else:
            del self.market_orders[order_type][symbol][0]
            if len(self.market_orders[order_type][symbol]) == 0:
                del self.orders[order_type][symbol]

    def execute_transaction(self, buyer, seller, symbol, volume, price):
        self.participants[buyer][symbol] += volume
        self.participants[seller][symbol] -= volume

        self.participants[buyer]['CASH'] -= volume * price
        self.participants[seller]['CASH'] += volume * price
