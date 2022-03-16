import numpy as np

def static(freq):
    """
    A static frequency.
    
    Parameters
    ----------
    freq : float
        static frequency in GHz

    Returns
    -------
    list
        list containing frequency profile
    
    """
    return [freq]

def ramp(start,end,steps):
    """
    A frequency ramp from a defined start and end step.
    
    Parameters
    ----------
    start : float
        start frequency in GHz
    end : float
        end frequency in GHz
    steps : int
        number of steps in the frequency ramp

    Returns
    -------
    list
        list containing frequency profile
    
    """
    return list(np.linspace(start,end,steps))