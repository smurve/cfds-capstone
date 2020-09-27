import abc

from markets.realistic import AbstractInvestor


class AbstractMarketScenario(abc.ABC):

    @abc.abstractmethod
    def register_investors(self, *investors: AbstractInvestor):
        pass

    @abc.abstractmethod
    def tick(self):
        pass

    @abc.abstractmethod
    def identify_investors(self):
        pass
