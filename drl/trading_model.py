import numpy as np


class Observation:
    def __init__(self, s, a, r, s1):
        self.s = s
        self.a = a
        self.r = r
        self.s1 = s1
        
    def __repr__(self):
        return str([self.s, self.a, self.r, self.s1])
    

class Environment:
    def __init__(self, t_init):
        self.t = t_init
  
    def state(self):
        raise Exception("Must implement state() in subclass!")
    
    def step(self, newp):        
        raise Exception("Must implement step() in subclass!")

    
class MarketEnvironment(Environment):
    """
    Environment Wrapper for a market simulator
    
    """
    def __init__(self, market, return_scale, weight_scale, n_hist, portfolio, t_init):
        """
        parameters:
        market: a StockMarket instance
        return_scale: the scale factor to be applied to the daily returns
        weight_scale: the scale factor to be applied to the portfolio weights
        n_hist: the number of returns to consider back from the present
        portfolio: initial portfolio in units of the risk-free asset (say: cash)
        t_init: The time step to begin with
        """
        super().__init__(t_init)
        self.market = market
        self.return_scale = return_scale
        self.weight_scale = weight_scale
        self.n_history = n_hist
        self.portfolio = np.array(portfolio)
        self.n_portfolio = len(portfolio)
        self.initial_wealth = np.sum(portfolio)
        self.total_fees = 0
        
    def state(self):
        mh = self.market.log_return_history(self.n_history, self.t)
        mh = self.return_scale * mh.reshape(1, self.n_history, self.market.n_securities, 1)
        pw = self.normalized_holdings()
        pw = self.weight_scale * pw.reshape(1, self.n_portfolio)
        return mh, pw

    def normalized_holdings(self):
        """
        "normalized" with respect to the initial wealth
        """
        return (self.portfolio / self.initial_wealth).astype(np.float32)
    
    def step(self, newp):        
        s = (self.market.log_return_history(self.n_history, self.t), self.normalized_holdings())
        a = np.array(newp).astype(np.float32)
        self.rebalance(newp)
        w = self.wealth()
        self.tick()
        r = np.log(self.wealth() / w)
        s1 = (self.market.log_return_history(self.n_history, self.t), self.normalized_holdings())
        return Observation(s, a, r, s1)

    def rebalance(self, newp):
        newp = np.array(newp) * self.wealth()
        tx = np.sum(np.abs(self.portfolio - newp))
        self.portfolio = newp
        cost = tx * self.market.fee
        self.portfolio[0] -= cost
        self.total_fees = round(self.total_fees + cost, 2)
        return self
    
    def cash(self):
        return self.portfolio[0]
    
    def wealth(self):
        return np.sum(self.portfolio)
    
    def tick(self):
        old_prices = self.market.prices(self.t)
        self.t += 1
        ratio = self.market.prices(self.t) / old_prices
        
        # portfolio[0] is the cash position
        for i in range(self.n_portfolio - 1):
            self.portfolio[i + 1] *= ratio[i]
            
        return self.t
    
    def __repr__(self):
        return "wealth: %s, portfolio: %s" % (
            np.round(self.wealth(), 2), np.round(self.portfolio, 2))


class StockMarket:
    def __init__(self, fee):
        self.fee = fee
        self.n_securities = 0

        
class MarketFromData(StockMarket):
    """
    creates a market wrapper for an array or list of shape [N_STOCKS, N_PRICES]
    """
    def __init__(self, data, duration, nh, fee):
        """
        data: an array or list of shape [n_stocks, n_prices]
        nh: max. number of prices in history
        duration: the length of the period that can be served
        requires len(data) == duration + nh
        """
        super().__init__(fee)
        self.duration = duration
        self.nh = nh
        self.data = np.array(data)
        self.n_securities = np.shape(self.data)[0]
        self.fee = fee
        length = np.shape(self.data)[1]
        if length != duration + nh:
            raise ValueError("record length not sum of duration and history.")
        # Need one more for the log returns
        np.append(self.data, self.data[:, -1:], axis=-1)
                    
    def log_return_history(self, nh, t):
        if t < 0 or t >= self.duration:
            raise ValueError("t must be between %s and %s" % (0, self.duration - 1))
        if nh > self.nh or nh <= 0:
            raise ValueError("t must be between %s and %s" % (1, self.nh))
        t += self.nh + 1
        
        h = self.data[:, t - nh - 1: t]
        return np.log(h[:, 1:] / h[:, :-1]).T
        
    def prices(self, t):
        return self.data[:, t]
