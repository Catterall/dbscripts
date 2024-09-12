from os.path import exists


def check_path(func):
    """
    ? A decorator for raising an OSError if a path argument does not exist.
    
    ! The path argument MUST be the first argument of the method.
    """
    def wrapper(*args, **kwargs):
        if not exists(args[1]):
            raise OSError(f'The provided path, "{args[1]}", could not be found.')
        return func(*args, **kwargs)
    return wrapper
