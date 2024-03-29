class B2CloudError(Exception):
    def __init__(self, message):
        self.message = message

class LoginError(B2CloudError):
    pass
