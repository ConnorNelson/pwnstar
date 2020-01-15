import time


class Proxy:
    def __init__(self):
        self.gateway_write = None
        self.gateway_write_eof = None
        self.gateway_close = None
        self.target_write = None
        self.target_write_eof = None
        self.target_get_returncode = None
        self.history = []

    def on_recv(self, data, fd=None):
        self.history.append({
            'direction': 'output',
            'data': data,
            'fd': fd,
            'time': time.time()
        })
        return data

    def on_send(self, data, fd=None):
        self.history.append({
            'direction': 'input',
            'data': data,
            'fd': fd,
            'time': time.time()
        })
        return data

    def on_exit(self):
        history = [
            {
                k: v if type(v) is not bytes else v.decode('latin')
                for k, v in e.items()
            }
            for e in self.history
        ]
        data = {
            'interaction': history,
            'return_code': self.target_get_returncode() if self.target_get_returncode else None
        }

        return data
