from abc import ABC, abstractmethod
from typing import List, Dict

from .Order import Order


class AbstractMarketMaker(ABC):
    """
    The public interface of a MarketMaker
    """

    @abstractmethod
    def register_participant(self, investor):
        """
        register a participant and her portfolio
        :param investor: the investor
        """

    @abstractmethod
    def submit_orders(self, orders: List[Order]):
        """
        submit orders for a particular stock, identified by symbol
        :param orders: list of Orders
        """

    @abstractmethod
    def get_prices(self) -> Dict[str, Dict[str, float]]:
        """
        Get bid-ask and last tx prices.
        :return: Dict of Dict of like so:
            {'SYMBOL': {'bid': 100, 'ask': 101, 'last': 100.3}, ...}
        """

    @abstractmethod
    def trades_in(self, stock: str) -> bool:
        """
        :param stock: A stock symbol
        :return: wether or not this market maker trades with this stock
        """

    @abstractmethod
    def osid(self) -> str:
        """
        :return: a string consisting of process id and instance id
        """
