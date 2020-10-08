from __future__ import annotations

import abc
from typing import List, Dict

from .Clock import Clock
from .Order import Order, OrderType
from .Stock import Stock


class AbstractInvestor(abc.ABC):

    @abc.abstractmethod
    def get_name(self) -> str:
        pass

    @abc.abstractmethod
    def get_qname(self) -> str:
        """
        :return: the qualified name = name + OSID
        """
        pass

    @abc.abstractmethod
    def tick(self, clock: Clock):
        pass

    @abc.abstractmethod
    def get_stock_symbols(self) -> List[str]:
        """
        :return: a list of the stocks traded by this investor
        """
        pass

    @abc.abstractmethod
    def register_with(self, market_maker: AbstractMarketMaker, symbol: str):
        pass

    @abc.abstractmethod
    def report_tx(self, order_type: OrderType, symbol: str, volume: float, price: float, amount: float):
        pass

    @abc.abstractmethod
    def get_portfolio(self):
        pass

    @abc.abstractmethod
    def osid(self) -> str:
        pass


class AbstractMarket(abc.ABC):

    @abc.abstractmethod
    def get_stocks(self) -> List[Stock]:
        pass

    @abc.abstractmethod
    def get_intrinsic_value(self, symbol: str, day: int) -> float:
        pass


class AbstractMarketMaker(abc.ABC):
    """
    The public interface of a MarketMaker
    """

    @abc.abstractmethod
    def register_participant(self, investor: AbstractInvestor):
        """
        register a participant and her portfolio
        :param investor: the investor
        """

    @abc.abstractmethod
    def submit_orders(self, orders: List[Order]):
        """
        submit orders for a particular stock, identified by symbol
        :param orders: list of Orders
        """

    @abc.abstractmethod
    def get_prices(self) -> Dict[str, Dict[str, float]]:
        """
        Get bid-ask and last tx prices.
        :return: Dict of Dict of like so:
            {'SYMBOL': {'bid': 100, 'ask': 101, 'last': 100.3}, ...}
        """

    @abc.abstractmethod
    def trades_in(self, stock: str) -> bool:
        """
        :param stock: A stock symbol
        :return: wether or not this market maker trades with this stock
        """

    @abc.abstractmethod
    def osid(self) -> str:
        """
        :return: a string consisting of process id and instance id
        """
