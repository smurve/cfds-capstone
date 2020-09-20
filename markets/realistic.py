from collections import OrderedDict
from typing import Optional, Dict, List, Tuple
from uuid import UUID
from copy import deepcopy

from markets.abstract import AbstractMarketMaker
from markets.orders import Order, OrderType


class MarketMaker(AbstractMarketMaker):

    def __init__(self, symbols: List[str]):

        self.symbols = symbols
        if 'CASH' not in symbols:
            self.symbols.append('CASH')

        self.participants: Dict[UUID, Dict[str, float]] = {}
        self.highest_bid: Dict[str, Optional[Order]] = {}
        self.lowest_ask: Dict[str, Optional[Order]] = {}

        self.bid = {}
        self.ask = {}
        for symbol in symbols:
            self.bid[symbol] = OrderedDict()
            self.ask[symbol] = OrderedDict()

        # API V2.0
        self.orders: Dict[OrderType, Dict[str, OrderedDict]] = {}
        for order_type in OrderType:
            self.orders[order_type] = {}
            for symbol in symbols:
                self.orders[order_type][symbol] = OrderedDict()
        self.candidates = {
            OrderType.BID: {symbol: None for symbol in symbols},  # highest bid
            OrderType.ASK: {symbol: None for symbol in symbols}  # lowest ask
        }

    def register_participant(self, uuid: UUID, portfolio: Dict[str, float]):
        if not all([key in self.symbols for key in portfolio.keys()]):
            raise ValueError("Illegal portfolio: Not all given assets are supported here.")
        self.participants[uuid] = portfolio

    def submit_orders(self, symbol: str, orders: List[Order]):
        if symbol not in self.symbols:
            raise ValueError(f"Illegal order: symbol {symbol} no traded here.")
        for order in orders:
            order = deepcopy(order)
            if order.symbol not in self.symbols:
                raise ValueError(f"Illegal order: symbol {symbol} no traded here.")

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
        queue = self.orders[order_type][symbol]
        if queue.get(price) is None:
            queue[price] = []

        queue[price].append(order)

    def process_order(self, order: Order, candidate: Order):
        done = False
        while not done:
            order, done = self.process_order_maybe_partially(order, candidate)
            if not done:
                candidate = self.candidates[order.order_type.other()].get(order.symbol)

    def process_order_maybe_partially(self, order: Order, candidate: Order) -> Tuple[Optional[Order], bool]:
        bid, ask = (order, candidate) if order.order_type == OrderType.BID else (candidate, order)
        symbol = bid.symbol
        if ask.price <= bid.price:
            tx_price = ask.price
            tx_volume = min(ask.amount, bid.amount)
            bid.amount -= tx_volume
            ask.amount -= tx_volume
            self.execute_transaction(buyer=bid.other_party,
                                     seller=ask.other_party,
                                     symbol=symbol,
                                     volume=tx_volume,
                                     price=tx_price)
            if candidate.amount == 0:
                # candidate is exhausted, remove it from the queue
                self.remove_order(candidate)

                # next candidate price is popped from top (lowest_ask) or bottom (highest_bid)
                order_type = candidate.order_type
                prices = self.orders[order_type][symbol].keys()
                if len(prices) > 0:
                    pop_index = 0 if order_type == OrderType.BID else -1
                    new_price = list(self.orders[order_type][symbol].keys())[pop_index]

                    # pick the least recent order of that price as new candidate
                    self.candidates[candidate.order_type][symbol] = self.orders[order_type][symbol][new_price][0]
                else:
                    self.candidates[candidate.order_type][symbol] = None

            if order.amount == 0:
                return None, True
            else:
                return order, False
        else:
            self.register_order(order)

        return None, True

    def remove_order(self, order):
        symbol, order_type, price = order.symbol, order.order_type, order.price
        del self.orders[order_type][symbol][order.price][0]
        if len(self.orders[order_type][symbol][price]) == 0:
            del self.orders[order_type][symbol][order.price]

    def execute_transaction(self, buyer, seller, symbol, volume, price):
        self.participants[buyer][symbol] += volume
        self.participants[seller][symbol] -= volume

        self.participants[buyer]['CASH'] -= volume * price
        self.participants[seller]['CASH'] += volume * price
