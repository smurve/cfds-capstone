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
            if order.order_type == OrderType.BID:
                self.process_buy_order(symbol, order)
            elif order.order_type == OrderType.ASK:
                self.process_sell_order(symbol, order)
            else:
                raise ValueError(f"Can't handle {str(order)}")

    def process_buy_order(self, symbol: str, order: Order):
        candidate = self.lowest_ask.get(symbol)
        if not candidate or candidate.price > order.price:
            # No candidate or no match -> register for later
            self.register_bid(symbol, order)
        else:
            done = False
            while not done:
                order, done = self.try_execute_bid(order)

    def process_sell_order(self, symbol: str, order: Order):
        candidate = self.highest_bid.get(symbol)
        if not candidate or candidate.price < order.price:
            # No candidate or no match -> register for later
            self.register_ask(symbol, order)
        else:
            done = False
            while not done:
                order, done = self.try_execute_ask(order)

    def register_ask(self, symbol: str, order: Order):
        # if there's no ask yet, or the current ask is lower, we've got a new low
        if not self.lowest_ask.get(symbol) or order.price < self.lowest_ask[symbol].price:
            self.lowest_ask[symbol] = order

        if self.ask[symbol].get(order.price) is None:
            self.ask[symbol][order.price] = []

        self.ask[symbol][order.price].append(order)

    def register_bid(self, symbol: str, order: Order):
        if self.bid[symbol].get(order.price) is None:
            self.bid[symbol][order.price] = []

        # if there's no bid yet, or the current bid is higher, we've got a new high
        if not self.highest_bid.get(symbol) or order.price > self.highest_bid[symbol].price:
            self.highest_bid[symbol] = order

        self.bid[symbol][order.price].append(order)

    def try_execute_bid(self, bid: Order) -> Tuple[Optional[Order], bool]:
        symbol = bid.symbol
        ask = self.lowest_ask[symbol]
        if ask.price <= bid.price:
            tx_price = ask.price
            tx_volume = min(ask.amount, bid.amount)
            bid.amount -= tx_volume
            ask.amount -= tx_volume
            self.execute_bid(buyer=bid.other_party,
                             seller=ask.other_party,
                             symbol=symbol,
                             volume=tx_volume,
                             price=tx_price)
            if bid.amount == 0:
                return None, True

            if ask.amount == 0:
                self.remove_ask(ask)
                # the lowest ask is exhausted -> determine new low_ask
                new_low = list(self.ask[symbol].keys())[-1]
                self.lowest_ask[symbol] = self.ask[symbol][new_low][0]
                return bid, False
        else:
            self.register_bid(symbol, bid)

        return None, True

    def remove_ask(self, order: Order):
        symbol = order.symbol
        del self.ask[symbol][order.price][0]
        if len(self.ask[symbol][order.price]) == 0:
            del self.ask[symbol][order.price]

    def remove_bid(self, order: Order):
        symbol = order.symbol
        del self.bid[symbol][order.price][0]
        if len(self.bid[symbol][order.price]) == 0:
            del self.bid[symbol][order.price]

    def try_execute_ask(self, ask: Order) -> Tuple[Optional[Order], bool]:
        symbol = ask.symbol
        bid = self.highest_bid[symbol]
        if ask.price <= bid.price:
            tx_price = ask.price
            tx_volume = min(bid.amount, ask.amount)
            ask.amount -= tx_volume
            bid.amount -= tx_volume
            self.execute_bid(buyer=bid.other_party,
                             seller=ask.other_party,
                             symbol=symbol,
                             volume=tx_volume,
                             price=tx_price)
            if ask.amount == 0:
                return None, True

            if bid.amount == 0:
                self.remove_bid(bid)
                # the highest bid is exhausted -> determine new high_bid
                new_high = list(self.bid[symbol].keys())[0]
                self.highest_bid[symbol] = self.bid[symbol][new_high][0]
                return ask, False
        else:
            self.register_ask(symbol, ask)

        return None, True

    def execute_bid(self, buyer, seller, symbol, volume, price):
        self.participants[buyer][symbol] += volume
        self.participants[seller][symbol] -= volume

        self.participants[buyer]['CASH'] -= volume * price
        self.participants[seller]['CASH'] += volume * price
