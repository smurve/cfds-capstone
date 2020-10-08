from typing import List

from .AbstractMarketScenario import AbstractMarketScenario
from .Clock import Clock
from .abstract import AbstractMarketMaker
from .remotes import AsyncMarketMaker, AsyncInvestor


class RayMarketScenario(AbstractMarketScenario):

    def __init__(self, clock: Clock):
        super().__init__(clock)

    def register_investors(self, *investors):
        investors = [AsyncInvestor(investor) for investor in investors]
        self.investors += investors
        for investor in investors:
            self.try_associate_market_makers(investor)

        return list(investors)

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
