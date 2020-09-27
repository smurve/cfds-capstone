import uuid
from typing import Dict

from . import MarketMaker
from .AbstractInvestor import AbstractInvestor


class MomentumInvestor(AbstractInvestor):

    def __init__(self,
                 portfolio: Dict[str, float],
                 market_maker: MarketMaker,
                 name: str = None,
                 unique_id: uuid.UUID = uuid.uuid4()):
        self.name = name
        self.unique_id = unique_id
        self.market_maker = market_maker
        market_maker.register_participant(unique_id, portfolio)

    def __repr__(self):
        return self.name if self.name else str(self.unique_id)

    def tick(self) -> str:
        return 'OK'

    def identify(self) -> str:
        return self.name if self.name else self.unique_id
