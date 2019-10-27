import numpy as np
from matplotlib import pyplot as plt


def plot_behaviour(actor, env, duration, positions):
    """
    duration: duration in time steps
    positions: which of the actions to display
    """
    from copy import deepcopy
    env = deepcopy(env)
    wealth = []
    sin = []
    cos = []
    psin = []
    pcos = []
    cash = []

    mh, pw = env.state()
    for i in range(duration):
        action = actor([mh, pw]).numpy()[0]
        obs = env.step(action)

        mh, pw = env.state()

        wealth.append(env.wealth() / 1e8)
        sin.append(obs.s[0][-1][0])
        cos.append(obs.s[0][-1][1])
        psin.append(action[1] / 100)
        pcos.append(action[2] / 100)
        cash.append(action[0] / 100)

    plt.plot(sin)
    plt.plot(cos)
    if 1 in positions: 
        plt.plot(psin)
    if 2 in positions: 
        plt.plot(pcos)
    plt.plot(wealth)
    if 0 in positions: 
        plt.plot(cash)
    return env

        
def validate(actor, env, duration, start_at=0):
    from copy import deepcopy
    env = deepcopy(env)
    env.t = start_at
    w0 = env.wealth()
    mh, pw = env.state()
    for i in range(duration):
        action = actor([mh, pw]).numpy()[0]
        env.step(action)
        mh, pw = env.state()
    return env.wealth() / w0, env.total_fees


def validate_samples(actor, env, duration, n_samples):
    """
    Validate the actor on the environment using n_samples trajectories of the given duration
    """
    ret, fee = np.mean([
        validate(actor, env, duration,
                 start_at=np.random.randint(2000)) 
        for _ in range(n_samples)],
        axis=0)  
    return ret, round(fee)


def qfun_from_rewards(rewards, gamma):
    """
    calculate the Q-function from the rewards collected on a given trajectory
    """
    q = 0
    tqvals = []
    for t in range(len(rewards) - 1, -1, -1):
        q = rewards[t] + gamma * q
        tqvals.append(q)
    tqvals = np.array(tqvals[::-1])
    return tqvals


def trading_trajectory(actor, env, noise, duration, hold):
    """
    returns six columns representing the S A R S_1 values collected on the trajectory
    Here that is:         S      A    R     S_1
    represented by:   mhs, pws, acs, rs, mh1s, pw1s
    
    Parameters:
    periods: number of periods of trading and holding
    hold: number of days to hold (on to an action)
    """
    def vstack(x, y):
        if x is None:
            return y
        return np.vstack([x, y])
    
    from copy import deepcopy
    env = deepcopy(env)

    mhs, pws, mh1s, pw1s, acs, rs = 6 * [None]

    for i in range(duration):

        # observe
        mh, pw = env.state()
        mh = mh.astype(np.float32)
        pw = pw.astype(np.float32)
        mhs = vstack(mhs, mh)
        pws = vstack(pws, pw)

        # determine the action
        a = actor([mh, pw])
        action = a.numpy()[0]
        if noise is not None:
            action = noise(action, {'step': i})
        acs = vstack(acs, [action])

        # Act and collect total reward over the holding period
        r = 0
        for _ in range(hold):
            observation = env.step(action)
            r += observation.r
        rs = vstack(rs, [r])

        # next state
        mh1, pw1 = env.state()
        mh1s = vstack(mh1s, mh1)
        pw1s = vstack(pw1s, pw1)

    return (mhs.astype(np.float32), 
            pws.astype(np.float32), 
            acs.astype(np.float32), 
            rs.astype(np.float32), 
            mh1s.astype(np.float32), 
            pw1s.astype(np.float32))
