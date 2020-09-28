import ray

from .AbstractInvestor import AbstractInvestor


@ray.remote
class RayInvestor:

    def __init__(self, delegate: AbstractInvestor):
        self.delegate: AbstractInvestor = delegate

    def tick(self):
        self.delegate.tick()

    def identify(self) -> str:
        ip = ray.services.get_node_ip_address()  # noqa (services not exposed)
        return f'{self.delegate.identify()}@{ip}'


class AsyncInvestor(AbstractInvestor):

    def __init__(self, delegate: AbstractInvestor):
        self.delegate = RayInvestor.remote(delegate)

    def tick(self):
        self.delegate.tick.remote()

    def identify(self) -> str:
        return ray.get(self.delegate.identify.remote())
