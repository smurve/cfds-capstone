import logging
from collections import OrderedDict
from copy import deepcopy
from typing import Optional, Dict, List, Tuple, Union

from .common import ScenarioError
from .Clock import Clock
from .abstract import AbstractMarketMaker, AbstractInvestor, AbstractParticipant, AbstractStatistician
from .Order import Order, OrderType, ExecutionType


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
        :param initial_prices: a map like so {'TSMC': 121.0, ...}
        """
        self.logger = logging.getLogger(self.__class__.__name__)

        self.symbols = list(initial_prices.keys())
        self.mrtxp = deepcopy(initial_prices)

        # like {uuid: {'portfolio': {'TSLA': 1200}, 'contact': AbstractInvestor}
        self.participants: Dict[str, Dict[str, Union[AbstractInvestor, Dict[str, float]]]] = {}

        self.statistician = None

        self.orders: Dict[OrderType, Dict[str, OrderedDict]] = {}
        self.market_orders: Dict[OrderType, Dict[str, List[Order]]] = {}
        for order_type in OrderType:
            self.orders[order_type] = {}
            self.market_orders[order_type] = {}
            for symbol in initial_prices:
                self.orders[order_type][symbol] = OrderedDict()
                self.market_orders[order_type][symbol] = []

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

    def register_participant(self, other_participant: AbstractParticipant):
        if isinstance(other_participant, AbstractInvestor):
            self.register_investor(other_participant)
            self.logger.info(f"Registered Investor{other_participant.get_qname()}")
        elif isinstance(other_participant, AbstractStatistician):
            self.register_statistician(other_participant)
            self.logger.info(f"Registered Statistician {other_participant.osid()}")
        else:
            self.logger.error(f"Unknown participant class: {type(other_participant)}")
            raise ScenarioError(f"Unknown participant class: {type(other_participant)}")

    def register_statistician(self, statistician):
        self.statistician = statistician

    def register_investor(self, investor: AbstractInvestor):
        portfolio = investor.get_portfolio()
        if not all([key in self.symbols for key in portfolio.keys() if key != 'CASH']):
            self.logger.error(f"Can't register {investor.get_qname()}: Not all given assets are supported here.")
            raise ValueError("Illegal portfolio: Not all given assets are supported here.")
        self.participants[investor.get_qname()] = {'portfolio': portfolio, 'contact': investor}
        self.logger.info(f" {self.osid()}: Registered participant {investor.get_qname()}")

    def submit_orders(self, orders: List[Order], clock: Clock):
        self.logger.debug(f"[{str(clock)}]: Received {len(orders)} order" + ("s" if len(orders) != 1 else ""))
        for order in orders:
            if order.symbol not in self.symbols:
                self.logger.error(f"Illegal order: symbol {order.symbol} not traded here.")
                self.logger.error(f"Order: {str(order)} subitted by {order.other_party}")
                continue
            if order.amount <= 0:
                self.logger.warning(f"Illegal order: amount is {order.amount}.")
                self.logger.warning(f"Order: {str(order)} subitted by {order.other_party}")

            candidate = self.find_candidate(order, clock)
            while candidate and order:
                order_remainder, candidate_remainder = self.process_order(order, candidate, clock)

                if not candidate_remainder:
                    self.remove_candidate_from_order_book(candidate)
                    candidate = self.find_candidate(order, clock)
                else:
                    self.replace_candidate_with_remainder(candidate_remainder)
                    candidate = candidate_remainder

                order = order_remainder

            if order:
                if order.expires_at <= clock.seconds:
                    self.participants[order.other_party]['contact'].report_expiry(order)
                else:
                    self.register_order(order)

    def find_candidate(self, order: Order, clock: Clock) -> Optional[Order]:
        """
        1) Cleanup 1: While limit candidate expired, replace it with the next in succession
        2) Return eventual candidate if it matches. If not, proceed with 3)
        3) Cleanup 2: While market candidate expired, replace it with the next in succession
        4) Return eventual candidate if it matches, else None
        """
        for execution_type in [ExecutionType.LIMIT, ExecutionType.MARKET]:  # order matters: chcek LIMIT first
            candidate = self.find_new_candidate(execution_type, order.order_type.other(), order.symbol)
            while candidate and candidate.expires_at < clock.seconds:
                self.remove_candidate_from_order_book(candidate)
                self.participants[candidate.other_party]['contact'].report_expiry(candidate)

                candidate = self.find_new_candidate(execution_type, order.order_type.other(), order.symbol)
                if candidate and execution_type == ExecutionType.LIMIT:
                    self.candidates[candidate.order_type][candidate.symbol] = candidate

            if candidate and candidate.matches(order):
                return candidate

        return None

    def replace_candidate_with_remainder(self, remainder: Order):
        """
        Replace the respective (limit or market) candidate with the remainder after processing
        Replace the respective order in the orderbook, too.
        """
        if remainder.execution_type == ExecutionType.LIMIT:
            self.candidates[remainder.order_type][remainder.symbol] = remainder
            self.orders[remainder.order_type][remainder.symbol][remainder.price][0] = remainder
        else:
            self.market_orders[remainder.order_type][remainder.symbol][0] = remainder

    def process_order(self, order: Order, candidate: Order, clock: Clock) -> Tuple[Optional[Order], Optional[Order]]:
        """
        execute the matching part. Return remainder and None - depending on which order was larger
        The return order order Orders reflects the order in the method signatur: candidate last
        Return None, None for a perfect match
        """
        bid, ask, swapped = Order.as_bid_ask(order, candidate)
        tx_price = self.determine_price(bid, ask)
        tx_volume = min(ask.amount, bid.amount)

        new_bid, new_ask = Order.compute_remainders(bid, ask, tx_volume)

        self.logger.debug(f'Executing trade: {tx_volume} shares of {bid.symbol} for ${tx_price}')
        self.execute_transaction(buyer=bid.other_party,
                                 seller=ask.other_party,
                                 symbol=bid.symbol,
                                 volume=tx_volume,
                                 price=tx_price,
                                 clock=clock)
        self.mrtxp[bid.symbol] = tx_price

        return (new_ask, new_bid) if swapped else (new_bid, new_ask)

    def find_new_candidate(self, execution_type: ExecutionType, order_type: OrderType, symbol: str) -> Optional[Order]:
        """
        Find the next best registered order to serve the candidate role
        :param execution_type the execution type of the desired new candidate
        :param order_type: the order_type of the desired new candidate
        :param symbol: the symbol of the desired new candidate
        :return: the next best registered order to serve the candidate role, look for limit orders first
        """
        if execution_type == ExecutionType.LIMIT:
            # next candidate price is popped from top (lowest_ask) or bottom (highest_bid)
            relevant_orders = self.orders[order_type][symbol]
            prices = sorted(list(relevant_orders.keys()))
            if len(prices) > 0:
                pop_index = 0 if order_type == OrderType.ASK else -1
                new_price = prices[pop_index]

                # pick the least recent order of that price as new candidate
                if relevant_orders[new_price]:
                    return relevant_orders[new_price][0]

        elif execution_type == ExecutionType.MARKET:
            if self.market_orders[order_type].get(symbol):  # neither empty nor None
                return self.market_orders[order_type][symbol][0]

        return None

    def register_order(self, order: Order):
        order_type, symbol, price = order.order_type, order.symbol, order.price

        # for limit orders, set highest/lowest, if appropriate
        if order.execution_type == ExecutionType.LIMIT:
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

    def determine_price(self, bid: Order, ask: Order) -> float:
        if ask.execution_type == ExecutionType.LIMIT:
            return ask.price
        elif bid.execution_type == ExecutionType.LIMIT:
            return min(bid.price, self.get_prices()[ask.symbol]['last'])
        else:
            return self.mrtxp[ask.symbol]

    def remove_candidate_from_order_book(self, order):
        """
        Remove the order candidate from the order book. For limit orders it's the least recent with the best price
        For market orders it's simply the least recent one. Also remove limit candidates from the candidate dict
        """
        symbol, order_type, price = order.symbol, order.order_type, order.price
        if order.execution_type == ExecutionType.LIMIT:
            self.logger.debug("Removing Limit order from the books")
            if self.orders[order_type][symbol].get(price):
                top_orders = self.orders[order_type][symbol][price]
                if top_orders:
                    registered_order = top_orders[0]
                else:
                    self.logger.error(f"Inconsistency: target order to remove does not exist.")
                    self.logger.error(f"target: {str(order)} - no order with that price.")
                    return

                if order.same_as(registered_order):
                    del self.orders[order_type][symbol][price][0]
                    if len(self.orders[order_type][symbol][price]) == 0:
                        del self.orders[order_type][symbol][price]

                    candidates = self.candidates[order_type][symbol]
                    if not candidates:
                        self.logger.error(f"Inconsistency: There is no candidate to delete.")
                        self.logger.error(f"Order was: {str(order)}")
                    else:
                        if order.same_as(self.candidates[order_type][symbol]):
                            self.candidates[order_type][symbol] = None
                        else:
                            self.logger.error(f"Inconsistency: order is not the current candidate.")
                            self.logger.error(f"Order was: {str(order)}")

                else:
                    self.logger.error(f"Inconsistency: target order to remove does not exist.")
                    self.logger.error(f"target: {str(order)} - for removal: {str(registered_order)}")
                    return
        else:
            del self.market_orders[order_type][symbol][0]

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

        if self.statistician:
            self.logger.debug(f'Reporting tx to statistician:')
            self.statistician.report_transaction(symbol, volume, price, clock)

    def trades_in(self, stock: str) -> bool:
        return stock in self.symbols

    def osid(self) -> str:
        import os
        return f'({os.getpid()}-{id(self)})'
