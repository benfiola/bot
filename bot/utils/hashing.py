import hashlib
import json
from typing import Union


import pydantic


def hashify(data: Union[pydantic.BaseModel, dict]):
    """
    Serializes the provided dictionary (sorting all keys), and generates a hash string from it.
    :param data:
    :return:
    """
    if isinstance(data, pydantic.BaseModel):
        data = data.json(sort_keys=True)
    else:
        data = json.dumps(data, sort_keys=True)
    data = data.encode("utf-8")
    data = hashlib.sha256(data)
    data = data.hexdigest()
    return data
