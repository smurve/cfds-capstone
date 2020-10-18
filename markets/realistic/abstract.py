from __future__ import annotations

import abc
from typing import List, Dict, Tuple

import datetime as dt
import pandas as pd

from .Clock import Clock
from .Order import Order, OrderType
from .Stock import Stock


class AbstractParticipant(abc.ABC):
    """
    Abstracting common behaviour of all market participants
    """
    @abc.abstractmethod
    def register_participant(self, other_participant: AbstractParticipant, **kwargs):
        """
        register a participant and her portfolio
        :param other_participant: any other participant
        :param kwargs: any additional arguments that come with the participant
        """

    def osid(self) -> str:
        import os
        return f'({os.getpid()}-{id(self)})'

    @abc.abstractmethod
    def get_role(self) -> str:
        """
        :return: a string representation of the business role, such as: Investor, Statistician, MarketMaker
        """


class AbstractInvestor(AbstractParticipant):

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
    def report_tx(self, order_type: OrderType, symbol: str, volume: float,
                  price: float, amount: float, clock: Clock):
        pass

    @abc.abstractmethod
    def report_expiry(self, order: Order):
        pass

    @abc.abstractmethod
    def get_portfolio(self) -> Dict[str, float]:
        pass

    def get_role(self) -> str:
        return "Investor"


class AbstractMarket(abc.ABC):

    @abc.abstractmethod
    def get_stocks(self) -> List[Stock]:
        pass

    @abc.abstractmethod
    def get_intrinsic_value(self, symbol: str, day: int) -> float:
        pass


class AbstractMarketMaker(AbstractParticipant):
    """
    The public interface of a MarketMaker
    """

    @abc.abstractmethod
    def submit_orders(self, orders: List[Order], clock: Clock):
        """
        submit orders for a particular stock, identified by symbol
        :param orders: list of Orders
        :param clock: The respective current timestamp
        """

    @abc.abstractmethod
    def get_prices(self) -> Dict[str, Dict[str, float]]:
        """
        Get bid-ask and last tx prices.
        :return: Dict of Dict of like so:
            {'SYMBOL': {'bid': 100, 'ask': 101, 'last': 100.3}, ...}
        """

    @abc.abstractmethod
    def get_order_book(self) -> Dict[str, Dict[float, Tuple[str, float]]]:
        """
        :return: a dict of all order amount/price pairs
        """

    @abc.abstractmethod
    def trades_in(self, stock: str) -> bool:
        """
        :param stock: A stock symbol
        :return: wether or not this market maker trades with this stock
        """

    def get_role(self):
        return "MarketMaker"


class AbstractStatistician(AbstractParticipant):
    """
    Refactored all stats collection out of the market maker
    """

    @abc.abstractmethod
    def get_chart_data(self, symbol: str, date: dt.date) -> pd.Dataframe:
        pass

    @abc.abstractmethod
    def report_transaction(self, symbol: str, volume: float, price: float, clock: Clock):
        pass

    def get_role(self):
        return "Statistician"


class AbstractTradingStrategyFactory(abc.ABC):

    @staticmethod
    @abc.abstractmethod
    def create_strategy(**kwargs) -> AbstractTradingStrategy:
        """
        :param kwargs: Implementation-specifig parames
        :return:
        """


class AbstractTradingStrategy(abc.ABC):

    @abc.abstractmethod
    def suggest_orders(self, prices_dict: Dict[str, Dict[str, Dict[str, float]]],
                       cash: float, cash_reserve: float,
                       clock: Clock) -> Dict[str, List[Order]]:
        """
        :param prices_dict: a dictionary like so: {'mm_osid': {'TSMC': {'bid': 10, 'ask': 11, 'last': 10.2}}}
        :param cash: The investor's current cash position
        :param cash_reserve: The investor's intended cash_reserve. Consult your strategy's doc for how this is used.
        :param clock: The current time represented by a Clock instance
        :return: A dict of mm_osid: List of Order
        """
