import ray

from markets.realistic import AbstractInvestor


@ray.remote
class RayInvestor:

    def __init__(self, delegate: AbstractInvestor):
        self.delegate = delegate

    def tick(self):
        self.delegate.tick()

    def identify(self) -> str:
        ip = ray.services.get_node_ip_address()  # noqa (services not exposed)
        return f'{self.delegate.identify()}@{ip}'
