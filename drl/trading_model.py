import numpy as np
import pickle
import glob
from markets.stocks_model import MarketFromData

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
        return mh.astype(np.float32), pw.astype(np.float32)

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

    
class EnvironmentFactory:

    def __init__(self, pattern, duration, n_hist, portfolio, 
                 return_scale, weight_scale, fee):
        self.duration = duration
        self.data = self.read_files(pattern)
        self.n_hist = n_hist
        self.portfolio = portfolio
        self.return_scale = return_scale
        self.weight_scale = weight_scale
        self.fee = fee
        
    @staticmethod
    def read_files(pattern):
        data = []
        files = glob.glob(pattern)
        assert files != [], "No such file: %s" % pattern
        for file in files:
            with open(file, 'rb') as file:
                r=0
                while True:
                    try: 
                        data.append(pickle.load(file))
                        r+=1
                    except EOFError:
                        break;
        return data
                        
    def new_env(self, index=None):
        
        index = index or np.random.randint(len(self.data))
        single_data = np.array([self.data[index][ticker]['price'] 
                                for ticker in self.tickers()])

        market = MarketFromData(single_data, self.duration, self.n_hist, self.fee)

        env = MarketEnvironment(
            market=market, 
            n_hist=self.n_hist, 
            t_init=0, 
            portfolio=self.portfolio,     
            return_scale = self.return_scale,
            weight_scale = self.weight_scale
        )
        return env
    
    def tickers(self):
        return list(self.data[0].keys())
    
    def prices_for(self, ticker, index):
        return self.data[index][ticker]['price']
