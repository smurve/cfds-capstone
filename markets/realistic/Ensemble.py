from typing import List, Dict

from .abstract import AbstractMarketMaker, AbstractInvestor, AbstractStatistician, AbstractMarket


class Ensemble:

    def __init__(self, markets: List[AbstractMarket],
                 market_makers: Dict[AbstractMarketMaker, AbstractStatistician],
                 investors: List[AbstractInvestor]):

        self.markets = markets
        self.market_makers = market_makers
        self.investors = investors
