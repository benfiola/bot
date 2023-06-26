class BotCommandError(Exception):
    """
    An error that can be raised by commands indicating user errors when invoking commands.

    Its message is intended to be sent back to the end-user.
    """

    message: str

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
