import functools
import inspect


def log(logger):
    def wrapper(func):
        signature = inspect.signature(func)
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            bound = signature.bind(*args, **kwargs)
            args_info = ', '.join([repr(arg) for arg in bound.args] +
                                  [f'{repr(key)}={repr(val)}' for key, val in bound.kwargs.items()])
            logger.debug(f"{func.__qualname__}({args_info})")
            return func(*args, **kwargs)
        return wrapped
    return wrapper
