from abc import ABC, abstractmethod
from typing import List
from uuid import UUID

from markets.orders import Order


class AbstractMarketMaker(ABC):

    @abstractmethod
    def register_participant(self, uuid: UUID, portfolio: dict):
        """
        register a participant and her portfolio
        :param uuid: the uuid identifier of the participant
        :param portfolio: a map of ticker: amount with at least a 'CASH' position
        """
        pass

    @abstractmethod
    def submit_orders(self, symbol: str, orders: List[Order]):
        """
        submit orders for a particular stock, identified by symbol
        :param symbol: name of the stock to transact
        :param orders: list of Orders
        """
        pass
