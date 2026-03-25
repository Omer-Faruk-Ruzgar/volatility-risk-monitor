import pandas as pd
from arch import arch_model

def compute_garch(returns: pd.Series) -> pd.Series:
    """
    Fit GARCH(1,1) and return conditional volatility series.

    Parameter:
        rerurns: pd.Series -> Daily log returns

    Return:
        pd.Series -> Annualisede conditional volatility    
    """

    model = arch_model(
        returns * 100,
        vol = 'Garch',
        p = 1, q = 1,
        rescale = False
    )

    result = model.fit(disp = 'off')
    return (result.conditional_volatility / 100) * (252 ** 0.5)
