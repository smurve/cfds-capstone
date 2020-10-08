import numpy as np
import pandas as pd

from .Order import Order, OrderType, ExecutionType


class TriangularOrderGenerator:
    """
    This class creates a set of adjacent orders that represent a particular given order in such a way
    that the price dynamics are smooth and continuous. This helps simulate larger liquidity
    and broader distribution of order prices despite a limited number of market participants.
    """

    def __init__(self, client_id: str):
        self.client_id = client_id

    def create_orders(self, p: float, tau: float, n: float, order_type: OrderType, n_orders: int):
        """
        creates a list of prices centered at p and share fractions the sum of which equals p times n
        :param p: the central price
        :param tau: the relative tolerance as fraction of p
        :param n: the number of shares to transact
        :param order_type: order type: BID or ASK
        :param n_orders: number of orders
        :return: A list of tuples representing Orders
        """

        # number of single orders to generate
        nu = n_orders + 1  # int(tau * p / self.split)

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

        return res[:-1] if order_type == OrderType.BID else res[-2::-1]

    def create_orders_df(self, symbol: str, p: float, tau: float, n: float, order_type: OrderType, n_orders: int):

        orders = self.create_orders(p=p, tau=tau, n=n, order_type=order_type, n_orders=n_orders)
        orders = np.array(orders).T
        orders = pd.DataFrame.from_dict({'price': orders[0], 'amount': orders[1]})
        orders['other_party'] = self.client_id
        orders['symbol'] = symbol
        orders['order_type'] = order_type

        return orders

    def create_orders_list(self, symbol: str, p: float, tau: float, n: float,
                           order_type: OrderType, execution_type: ExecutionType, expire_in_seconds: int, n_orders: int):
        """
        :return: an OrderedDict of orders with price as key
        """
        orders = self.create_orders_df(symbol, p, tau, n, order_type, n_orders)
        orders['expires_in_seconds'] = expire_in_seconds
        orders['execution_type'] = execution_type
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
