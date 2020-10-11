import abc
from typing import List
import logging

from .common import ScenarioError
from .abstract import AbstractInvestor, AbstractMarketMaker
from .Clock import Clock


class AbstractMarketScenario(abc.ABC):

    def __init__(self, clock: Clock):
        self.clock = clock
        self.investors: List[AbstractInvestor] = []
        self.market_makers: List[AbstractMarketMaker] = []
        self.logger = logging.getLogger(self.__class__.__name__)

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
    def tick(self, seconds: int):
        pass

    @abc.abstractmethod
    def identify_investors(self):
        pass

    def try_associate_market_makers(self, investor: AbstractInvestor):
        for symbol in investor.get_stock_symbols():
            found = False
            for market_maker in self.market_makers:
                if market_maker.trades_in(symbol):
                    investor.register_participant(market_maker, symbol=symbol)
                    market_maker.register_participant(investor)
                    self.logger.info(f'Registered investor {investor.osid()} with market maker {market_maker.osid()}')
                    found = True
            if not found:
                raise ScenarioError(f"Can't find a market maker supporting stock {symbol}")
