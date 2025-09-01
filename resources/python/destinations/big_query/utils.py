from datetime import datetime

def format_nanoseconds(nanoseconds: int):
    dt = datetime.fromtimestamp(nanoseconds / 1e9)
    return '{}.{:09.0f}'.format(dt.strftime('%Y-%m-%dT%H:%M:%S'), nanoseconds % 1e9)


def flatten_json(nested_json, separator='_'):
    """
    Flatten a nested JSON object.
    
    :param nested_json: The JSON object to flatten.
    :param separator: The separator to use between nested keys.
    :return: A flattened JSON object.
    """
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + separator)
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + separator)
                i += 1
        else:
            out[name[:-1]] = x

    flatten(nested_json)
    return out
