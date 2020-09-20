import datetime as dt
from dataclasses import dataclass
from enum import Enum
from uuid import UUID

import numpy as np
import pandas as pd


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
        return f'{self.order_type.value} {self.price} for {self.amount} shares of {self.symbol}'

    def precedes(self, other) -> bool:
        assert other.order_type == self.order_type
        return self.price > other.price if self.order_type == OrderType.BID else self.price < other.price


class TriangularOrderGenerator:
    """
    This class creates a set of adjacent orders that represent a particular given order in such a way
    that the price dynamics are smooth and continuous. This helps simulate larger liquidity
    and broader distribution of order prices despite a limited number of market participants.
    """

    def __init__(self, client_id: UUID, expiry: dt.date, split: float):
        self.client_id = client_id
        self.expiry = expiry
        self.split = split
        """
        params: split: the price diff between to subsequent partial orders
        """

    def create_orders(self, p: float, tau: float, n: float, order_type: OrderType):
        """
        creates a list of prices and share fractions the sum of which equals p times N

        params:
            p: bid or ask price
            N: number of shares, may be float
        """

        # number of single order to generate
        nu = int(tau * p / self.split)

        # lower and upper price bound
        p_lower = p * (1 - tau / 2)

        # upper price bound
        p_upper = p * (1 + tau / 2)

        # switching supports ASK orders
        if order_type == OrderType.ASK:
            p_upper, p_lower = p_lower, p_upper

        # price step
        delta_p = float(p_upper - p_lower) / nu

        # total transaction volume
        v = n * p

        a = self._find_a(p_lower, p_upper)(nu)
        b = self._find_b(p_lower, p_upper)(nu)

        alpha = self._alpha(v, nu, a, b)
        beta = self._beta(v, nu, a, b)

        res = [(round(p_lower + delta_p * (i + 1), 2),
                alpha + beta * (i + 1)
                )
               for i in range(nu)]

        return res if order_type == OrderType.BID else res[::-1]

    def create_orders_df(self, symbol: str, p: float, tau: float, n: float, order_type: OrderType):

        orders = self.create_orders(p=p, tau=tau, n=n, order_type=order_type)
        orders = np.array(orders).T
        orders = pd.DataFrame.from_dict({'price': orders[0], 'amount': orders[1]})
        orders['other_party'] = self.client_id
        orders['symbol'] = symbol
        orders['expiry'] = self.expiry
        orders['order_type'] = order_type

        return orders

    def create_orders_list(self, symbol: str, p: float, tau: float, n: float, order_type: OrderType):
        """
        :return: an OrderedDict of orders with price as key
        """
        orders = self.create_orders_df(symbol, p, tau, n, order_type)
        return [Order(**order) for order in orders.to_dict('records')]

    @staticmethod
    def _find_a(p_lower, p_upper):
        def a(nu):
            return nu * p_lower + (nu + 1) * (p_upper - p_lower) / 2

        return a

    @staticmethod
    def _find_b(p_lower, p_upper):
        def b(nu):
            return nu * (nu + 1) * p_lower / 2 + (p_upper - p_lower) * (nu + 1) * (2 * nu + 1) / 6

        return b

    @staticmethod
    def _beta(v, nu, a, b):
        return v / (b - nu * a)

    def _alpha(self, v, nu, a, b):
        return -nu * self._beta(v, nu, a, b)
