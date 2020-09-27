import datetime as dt
from dataclasses import dataclass
from enum import Enum
from typing import Tuple
from uuid import UUID


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
    other_party: UUID
    order_type: OrderType
    execution_type: ExecutionType
    symbol: str
    amount: float
    price: float
    expiry: dt.datetime

    def __repr__(self):
        return f'{self.order_type.value} ' \
               f'{self.price if self.execution_type == ExecutionType.LIMIT else ExecutionType.MARKET.value} ' \
               f'for {self.amount} shares of {self.symbol}'

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

    @staticmethod
    def as_bid_ask(order: 'Order', candidate: 'Order') -> Tuple['Order', 'Order']:
        return (order, candidate) if order.order_type == OrderType.BID else (candidate, order)
