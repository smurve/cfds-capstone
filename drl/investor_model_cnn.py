import tensorflow as tf
import tensorflow.keras as tk
import tensorflow.keras.layers as tkl


def new_actor(n_market, n_history, n_filters, n_portfolio, layers, activation='elu'):
    inp_mh = tk.Input(shape=[n_history, n_market, 1], dtype=tf.float32)
    inp_pw = tk.Input(shape=[n_portfolio], dtype=tf.float32)

    conv = tkl.Conv2D(activation='tanh', filters=n_filters, padding='valid',
                      kernel_size=[n_history, 1])
    reshape = tkl.Reshape([n_market * n_filters])
    concat = tkl.Concatenate(axis=-1)
    out = concat([reshape(conv(inp_mh)), inp_pw])

    # The dense policy head
    for i, u in enumerate(layers):
        out = tkl.Dense(units=u, activation=activation)(out)
    out = tkl.Dense(units=n_portfolio, activation='softmax')(out)

    model = tk.Model([inp_mh, inp_pw], out)
    model.n_history = n_history
    model.n_market = n_market
    model.n_portfolio = n_portfolio
    return model


def new_critic(n_market, n_history, n_filters, n_portfolio, layers, activation='elu'):   
    inp_mh = tk.Input(shape=[n_history, n_market, 1], dtype=tf.float32)
    inp_pw = tk.Input(shape=[n_portfolio], dtype=tf.float32)    
    inp_pa = tk.Input(shape=[n_portfolio], dtype=tf.float32)    
    
    conv = tkl.Conv2D(activation='tanh', filters=n_filters, padding='valid',
                      kernel_size=[n_history, 1])
    reshape = tkl.Reshape([n_market * n_filters])
    concat = tkl.Concatenate(axis=-1)
    out = concat([reshape(conv(inp_mh)), inp_pw, inp_pa])

    for i, u in enumerate(layers):
        out = tkl.Dense(units=u, activation=activation)(out)
    out = tkl.Dense(units=1, activation=None)(out)

    model = tk.Model(inputs=[inp_mh, inp_pw, inp_pa], outputs=out)
    model.n_history = n_history
    model.n_market = n_market
    model.n_portfolio = n_portfolio
    return model
