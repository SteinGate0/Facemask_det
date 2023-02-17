class DecodeError(Exception):
    def __init__(self, message):
        super().__init__()
        self.message= message
        self.code=-1
    def __str__(self):
        return self.message
