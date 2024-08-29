class Closed_pipe(Exception):
    def __init__(self, mensagem, error_code=None):
        super().__init__(mensagem)
        self.error_code = error_code