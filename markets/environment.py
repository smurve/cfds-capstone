import numpy as np
from markets.dynamic_market import Ask, Bid, Investor, MomentumInvestor

class TradingEnvironment:
    """
    This class represents the RL environment of a single investor. It comprises of a
    portfolio of holdings - which includes a cash position - and the market with its
    players, in this case a bunch of momentum investors with limited reason...;-)
    """
    def __init__(self, config, holdings, market, tx_cost):
        self.config = config
        self.investor = self.create_investor(holdings.copy())
        self.market = market
        self.other_investors = make_investors(config['num_investors'], holdings.copy())
        self.tx_cost = tx_cost
        
    def create_investor(self, holdings):
        cash = holdings['cash']
        del(holdings['cash'])
        return Investor("WB", cash, holdings)        
        
    def let_others_trade(self):
        for _ in range(self.config['num_rounds_per_day']):
            for investor in self.other_investors:
                investor.act(self.market)
    
    def total_wealth(self):

        wealth = self.investor.cash
        for ticker in self.investor.portfolio:
            size = self.investor.portfolio[ticker]
            wealth += size * self.market.price_for(ticker)[1]
        return round(wealth,3)
    
    def normalized_holdings(self):
        values = {}
        values['cash'] = self.investor.cash
        holdings = self.investor.portfolio
        for ticker in holdings:
            values[ticker] = holdings[ticker] * self.market.price_for(ticker)[1]
        w = self.total_wealth()
        return np.array([v/w for _,v in sorted(values.items())])
    
    def act(self, new_weights):
        """
        This constitutes a trading day. We act, and then the market moves on.
        """
        former_wealth = self.total_wealth()
    
        self.market.open()
        
        orders = self.create_orders(new_weights)
        for order in orders:
            self.market.execute(order)

            total_tx_volume = np.sum(
                [order.amount * order.price for order in orders])
        
        fee = total_tx_volume * self.tx_cost
        self.investor.cash = round(self.investor.cash - fee, 3)
        
        self.let_others_trade()
        self.market.close()
        
        return self.state_rep(former_wealth)
    
    def state_rep(self, former_wealth ):
        h = self.market.history
        returns = [ np.log(h[key][-1][1] / h[key][-2][1])
                    for key in h]
        returns = returns / np.sum(np.abs(returns))
        observations = np.hstack([self.normalized_holdings(), returns])
        return (observations, np.log(self.total_wealth()/former_wealth))
    
    def create_orders (self, new_weights):
        """
        Create an order book from the target portfolio weights
        new_weights: list of normalized weights of the holdings
        sorted by the holdings' ticker names, cash last
        """
        cur_weights = self.normalized_holdings()
        vols = ((new_weights - cur_weights) * self.total_wealth())[:-1]
        holdings = self.investor.portfolio
        tickers = sorted(holdings)
        prices = np.array([self.market.price_for(t) for t in tickers])

        # identify the correct prices for bid and ask transactions
        bid_asks = [p[(v<0).astype(int)] for v,p in zip(vols, prices)]

        orders = []
        for v, ba, t in zip(vols, bid_asks, tickers):
            amt = np.abs((v/ba).astype(int))
            B_or_A = Bid if v>0 else Ask
            if v != 0:
                orders.append(B_or_A(price=ba, amount=amt, 
                                  ticker=t, other_party=self.investor))
        return orders
    
    
def new_market(): 
    return Market(stocks=[aapl, msft, tsla], bid_ask=0.1)

def make_investors(num_investors, portfolio=None):
    from copy import deepcopy
    investors = []
    for i in range(num_investors):
        wr, wm, span = 0.3, 0.15, 20
        portfolio = deepcopy(portfolio) or {'AAPL': 10000, 'TSLA': 10000, 'MSFT': 10000}
        investor = MomentumInvestor("m-%s" % i, 1e8, portfolio, wr, wm, span)
        investors.append(investor)
    return investors