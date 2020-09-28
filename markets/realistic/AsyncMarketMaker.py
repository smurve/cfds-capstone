from typing import List
from uuid import UUID
import ray

from .AbstractMarketMaker import AbstractMarketMaker
from .Order import Order


@ray.remote
class RayMarketMaker:

    def __init__(self, delegate: AbstractMarketMaker):
        self.delegate = delegate

    def register_participant(self, uuid: UUID, portfolio: dict):
        pass

    def submit_orders(self, orders: List[Order]):
        pass


class AsyncMarketMaker(AbstractMarketMaker):

    def __init__(self, delegate: AbstractMarketMaker):
        self.delegate: AbstractMarketMaker = RayMarketMaker.remote(delegate)

    def register_participant(self, uuid: UUID, portfolio: dict):
        self.delegate.register_participant(uuid, portfolio)

    def submit_orders(self, orders: List[Order]):
        pass
