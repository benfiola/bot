class Client:
    """
    Implementation of a youtube API client.  Intended to make requests and parse responses from the youtube APIs.

    """

    _api_token: str | None

    def __init__(self, api_token: str | None):
        self._api_token = api_token

    def get_api_token(self) -> str:
        if not self._api_token:
            raise RuntimeError(f"api token not provided")
        return self._api_token
