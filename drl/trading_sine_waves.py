import numpy as np
from drl.trading_model import StockMarket


class SINX_COSX(StockMarket):
    """
    A super-silly, super-simple handcrafted market
    """
    def __init__(self, fee):
        super().__init__(fee)
        self.n_securities = 2
        
    def sinx(self, t):
        x = t + 3 * np.sin(t / 5.5)
        return (10 + np.sin(x / 10) + np.sin(x / 33) + np.sin(x / 100)).astype(np.float32)

    def cosx(self, t):
        x = 0.7 * t + 2 * np.cos(t / 5.5)
        return (12 + np.cos(x / 10) - np.cos(x / 23) + np.cos(x / 100)).astype(np.float32)
          
    def log_return_history(self, n_hist, t):
        h = np.array([[self.sinx(x), self.cosx(x)] for x in range(t - n_hist - 1, t)])
        return np.array(
            [np.log(h[1:, 0] / h[:-1, 0]),
             np.log(h[1:, 1] / h[:-1, 1])]).T

    def prices(self, t):
        return np.array([self.sinx(t), self.cosx(t)])
