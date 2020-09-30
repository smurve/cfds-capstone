from typing import List

from .AbstractMarketScenario import AbstractMarketScenario
from .AbstractMarketMaker import AbstractMarketMaker
from .AbstractInvestor import AbstractInvestor
from .Clock import Clock


class ScenarioError(ValueError):
    pass


class SynchronousMarketScenario(AbstractMarketScenario):

    def register_market_makers(self, *market_makers: AbstractMarketMaker) -> List[AbstractMarketMaker]:
        self.market_makers += list(market_makers)
        return list(market_makers)

    def __init__(self, clock=Clock()):
        super().__init__(clock)
        self.investors: List[AbstractInvestor] = []
        self.market_makers: List[AbstractMarketMaker] = []

    def register_investors(self, *investors: AbstractInvestor) -> List[AbstractInvestor]:
        # TODO: Should provide a matching MarketMaker to the investor
        for investor in investors:
            self.try_associate_market_makers(investor)

        self.investors += list(investors)

        return list(investors)

    def tick(self, seconds: int = 1):
        for investor in self.investors:
            investor.tick(self.clock.tick(seconds))

    def identify_investors(self):
        return [inv.identify() for inv in self.investors]

    def try_associate_market_makers(self, investor: AbstractInvestor):
        for stock in investor.get_stock_symbols():
            found = False
            for market_maker in self.market_makers:
                if market_maker.trades_in(stock):
                    investor.register_with(market_maker, stock)
                    found = True
            if not found:
                raise ScenarioError(f"Can't find a market maker supporting stock {stock}")
