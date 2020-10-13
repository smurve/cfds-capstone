from __future__ import annotations
import uuid
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Optional

from .Clock import Clock


class OrderType(Enum):
    ASK = 'ask'
    BID = 'bid'

    def other(self):
        if self == OrderType.ASK:
            return OrderType.BID
        else:
            return OrderType.ASK


class ExecutionType(Enum):
    MARKET = 'market'
    LIMIT = 'limit'


@dataclass()
class Order:
    other_party: str
    order_type: OrderType
    execution_type: ExecutionType
    symbol: str
    amount: float
    price: float
    expires_at: int
    order_id = uuid.uuid4()
    fraction_seqno = 0

    def __repr__(self):
        return f'{self.order_type.value} ' \
               f'{self.price if self.execution_type == ExecutionType.LIMIT else ExecutionType.MARKET.value} ' \
               f'for {self.amount} shares of {self.symbol} expiring at {str(Clock(initial_seconds=self.expires_at))}'

    def precedes(self, other: 'Order') -> bool:
        assert other.order_type == self.order_type
        if self.execution_type == ExecutionType.MARKET and other.execution_type == ExecutionType.LIMIT:
            return False
        elif self.execution_type == ExecutionType.LIMIT and other.execution_type == ExecutionType.MARKET:
            return True
        elif self.execution_type == ExecutionType.MARKET and other.execution_type == ExecutionType.MARKET:
            return False
        return self.price > other.price if self.order_type == OrderType.BID else self.price < other.price

    def matches(self, other: 'Order'):
        assert other.order_type != self.order_type
        ask, bid = (self, other) if other.order_type == OrderType.BID else (other, self)
        if self.execution_type == ExecutionType.LIMIT and other.execution_type == ExecutionType.LIMIT:
            return ask.price <= bid.price
        else:
            return True  # at least one of them is a market order

    def same_as(self, other: Order):
        """
        compare order_id and fraction_seqno.
        This is NOT equals(). It would still return True if price of volume change but the id match is True
        :param other:
        :return: True if order_id and fraction_seqno are equal
        """
        return self.order_id == other.order_id and self.fraction_seqno == other.fraction_seqno

    def equivalent(self, other: Order) -> bool:
        return (
            other is not None and
            self.order_type == other.order_type and
            self.other_party == other.other_party and
            self.execution_type == other.execution_type and
            self.symbol == other.symbol and
            self.amount == other.amount and
            (self.price == other.price or self.execution_type == ExecutionType.MARKET) and
            self.expires_at == other.expires_at
        )

    @staticmethod
    def compute_remainders(o1: Order, o2: Order, amount) -> Tuple[Optional[Order], Optional[Order]]:
        """
        :param o1: an order
        :param o2: another order that matches for a trade
        :param amount: the amount to be transacted using both orders
        :return:
        """
        if o1.amount == o2.amount == amount:
            return None, None
        if o2.amount == amount:
            return o1.reduced_by(amount), None
        elif o1.amount == amount:
            return None, o2.reduced_by(amount)
        else:
            return o1.reduced_by(amount), o2.reduced_by(amount)

    def reduced_by(self, amount: float) -> Order:
        cp = deepcopy(self)
        cp.fraction_seqno += 1
        cp.amount -= amount
        return cp

    @staticmethod
    def as_bid_ask(order: 'Order', candidate: 'Order') -> Tuple[Order, Order, bool]:
        """
        :param order: the incoming order
        :param candidate: the currently best candidate in the books
        :return: a tuple of the two orders - bid first - and whether they've been swapped
        """
        return (order, candidate, False) if order.order_type == OrderType.BID else (candidate, order, True)
