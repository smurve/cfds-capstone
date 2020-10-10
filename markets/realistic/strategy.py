from logging import Logger
from typing import Dict, List

from .Clock import Clock
from .Order import Order, ExecutionType, OrderType
from .TriangularOrderGenerator import TriangularOrderGenerator
from .abstract import AbstractMarket, AbstractTradingStrategy, AbstractTradingStrategyFactory


class PriceValueStrategy(AbstractTradingStrategy):
    """
    A strategy that generates order packages from looking at the investor and the market at a certain
    point in time.
    """
    def __init__(self, investor_qname: str, portfolio: Dict[str, float], market: AbstractMarket,
                 market_makers: Dict[str, str], max_volume_per_stock: float,
                 action_threshold: float, logger: Logger):
        """
        :param investor_qname:
        :param portfolio: a dict of symbol, number of shares
        :param market: the market
        :param market_makers: A dict assigning a market_maker osid to all names in the portfolio
        :param max_volume_per_stock:
        :param logger: Any logger suitable to the investor
        """
        self.investor_qname = investor_qname
        self.market = market
        self.market_makers = market_makers
        self.logger = logger
        self.portfolio = portfolio
        self.max_volume_per_stock = max_volume_per_stock
        self.kappa = 0.5  # larger kappa means orders more offset from the value -> better deals
        self.default_expire_after_seconds = 10
        self.n_orders_per_trade = 10
        self.order_generator = None  # will be lazily constructed before first usage
        self.action_threshold = action_threshold

    def suggest_orders(self, prices_dict: Dict[str, Dict[str, float]],
                       cash: float, cash_reserve: float,
                       clock: Clock) -> Dict[str, List[Order]]:

        orders_dict: Dict[str, List[Order]] = {}
        for symbol in self.portfolio.keys():
            self.debug(f"Looking at {symbol}")
            # market_maker = self.market_makers.get(symbol)
            # if not market_maker:
            #     self.error(f"No market maker for {symbol}")
            #     raise ScenarioError(f'No market maker for stock {symbol}.')

            price = prices_dict[symbol]['last']
            self.debug(f'Price for {symbol}: {price}')
            value = self.market.get_intrinsic_value(symbol, clock.day())
            self.debug(f'Value for {symbol}: {value}')

            if abs(1 - price / value) > self.action_threshold:
                tau = 2 * abs((price - value) / price)
                order_type = OrderType.BID if price < value else OrderType.ASK

                # kappa > 0 means a buffer from the value
                center = (1 + self.kappa) * price - self.kappa * value

                execution_type = ExecutionType.LIMIT
                n = self.determine_n_shares(price, cash, cash_reserve)
                expiry = self.determine_expiry(clock).seconds
                orders = self.create_orders_list(symbol, center, tau, n, order_type,
                                                 execution_type, expiry, self.n_orders_per_trade)
                orders_dict[symbol] = orders
        return orders_dict

    def determine_n_shares(self, price: float, cash: float, cash_reserve: float) -> float:
        volume = max(0., min(self.max_volume_per_stock, cash - cash_reserve))
        return int(volume / price) if volume > price else 0

    def determine_expiry(self, clock: Clock) -> Clock:
        return Clock(initial_seconds=clock.seconds + self.default_expire_after_seconds)

    def create_orders_list(self, symbol: str, p: float, tau: float, n: float,
                           order_type: OrderType, execution_type: ExecutionType,
                           expires_at: int, n_orders: int) -> List[Order]:

        # Lazily initialize order generator to get the correct ray-deployed qname
        if self.order_generator is None:
            self.order_generator = TriangularOrderGenerator(self.investor_qname)

        return self.order_generator.create_orders_list(symbol, p, tau, n, order_type, execution_type,
                                                       expires_at, n_orders)

    def debug(self, msg: str):
        self.logger.debug(f"{str(self)}: {msg}")

    def error(self, msg: str):
        self.logger.error(f"{str(self)}:: {msg}")


class PriceValueStrategyFactory(AbstractTradingStrategyFactory):

    def __init__(self, action_threshold: float):
        """
        :param action_threshold: percentage like abs((price/value-1)) before this strategy triggers.
        """
        self.action_threshold = action_threshold

    def create_strategy(self, investor_qname: str, portfolio: Dict[str, float], market_makers: Dict[str, str],
                        market: AbstractMarket, max_volume_per_stock: float, logger: Logger
                        ) -> AbstractTradingStrategy:
        return PriceValueStrategy(
            investor_qname=investor_qname,
            portfolio=portfolio,
            market_makers=market_makers,
            logger=logger,
            market=market,
            max_volume_per_stock=max_volume_per_stock,
            action_threshold=self.action_threshold
        )
