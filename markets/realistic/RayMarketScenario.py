import logging
from typing import List

from .Clock import Clock
from .AbstractMarketScenario import AbstractMarketScenario
from .abstract import AbstractMarketMaker, AbstractInvestor
from .SynchronousMarketScenario import ScenarioError
from .remotes import AsyncMarketMaker, AsyncInvestor


class RayMarketScenario(AbstractMarketScenario):

    def __init__(self, clock: Clock):
        super().__init__(clock)
        self.investors: List[AsyncInvestor] = []
        self.market_makers: List[AsyncMarketMaker] = []
        self.logger = logging.getLogger(__name__)

    def register_investors(self, *investors):
        investors = [AsyncInvestor(investor) for investor in investors]
        self.investors += investors
        for investor in investors:
            self.try_associate_market_makers(investor)

        return list(investors)

    def try_associate_market_makers(self, investor: AbstractInvestor):
        for stock in investor.get_stock_symbols():
            found = False
            for market_maker in self.market_makers:
                if market_maker.trades_in(stock):

                    investor.register_with(market_maker, stock)
                    self.logger.debug(f'Trying to register {investor.osid()} with market maker {market_maker.osid()}')
                    market_maker.register_participant(investor)
                    self.logger.debug(f'Registered investor {investor.osid()} with market maker {market_maker.osid()}')

                    found = True
            if not found:
                raise ScenarioError(f"Can't find a market maker supporting stock {stock}")

    def register_market_makers(self, *market_makers: AbstractMarketMaker) -> List[AbstractMarketMaker]:
        market_makers = [AsyncMarketMaker(market_maker) for market_maker in market_makers]
        self.market_makers += market_makers
        for market_maker in market_makers:
            self.logger.debug(f"Market Maker: {market_maker.osid()}")

        return market_makers

    def tick(self, seconds: int = 1):
        for investor in self.investors:
            investor.tick(self.clock.tick(seconds))

    def identify_investors(self):
        return [inv.get_qname() for inv in self.investors]
