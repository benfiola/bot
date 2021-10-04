from typing import Tuple


def split(msg: str) -> Tuple[str, str]:
    """
    Convenience method to split a string by spaces - returning
    the first part, and the remainder.

    Used primarily for command parsing.

    one, two = split("one two three")
    print(one, two) # "one", "two three"
    :param msg:
    :return:
    """
    parts = msg.split()
    return parts[0], " ".join(parts[1:])
