import abc


class AbstractInvestor(abc.ABC):

    @abc.abstractmethod
    def tick(self):
        pass

    @abc.abstractmethod
    def identify(self) -> str:
        pass
