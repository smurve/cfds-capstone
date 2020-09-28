import abc
from typing import List

from .AbstractInvestor import AbstractInvestor
from .AbstractMarketMaker import AbstractMarketMaker


class AbstractMarketScenario(abc.ABC):

    @abc.abstractmethod
    def register_investors(self, *investors: AbstractInvestor) -> List[AbstractInvestor]:
        """
        register the investors and return a list of references to those investors
        :param investors: A list of plain old python investors (POPIs)
        :return: a list of references, may be to remote instances of those
        """
        pass

    @abc.abstractmethod
    def register_market_makers(self, *market_makers: AbstractMarketMaker) -> List[AbstractMarketMaker]:
        """
        register the market makers and return a list of references to those investors
        :param market_makers: A list of plain old python MarketMakers
        :return: a list of references, may be to remote instances of those
        """
        pass

    @abc.abstractmethod
    def tick(self):
        pass

    @abc.abstractmethod
    def identify_investors(self):
        pass
