import time
import asyncio


class Proxy:
    def __init__(self):
        self.gateway_write = None
        self.gateway_write_eof = None
        self.gateway_close = None
        self.target_write = None
        self.target_write_eof = None
        self.target_get_returncode = None
        self.target_kill = None
        self.target_killed = False
        self.history = []
        self.exited = asyncio.Future()

    def attach_channel(self, channel, target_write, target_write_eof, target_get_returncode=None):
        attached_channel = channel
        attached_target_write = target_write
        attached_target_write_eof = target_write_eof
        original_target_write = self.target_write
        original_target_write_eof = self.target_write_eof
        def target_write(data, channel):
            if original_target_write:
                original_target_write(data, channel)
            if channel == attached_channel:
                attached_target_write(data)
        def target_write_eof(channel):
            if original_target_write_eof:
                original_target_write_eof(channel)
            if channel == attached_channel:
                attached_target_write_eof()
        self.target_write = target_write
        self.target_write_eof = target_write_eof
        if target_get_returncode:
            self.target_get_returncode = target_get_returncode

    def on_recv(self, data, channel=None):
        self.history.append({
            'direction': 'output',
            'data': data,
            'channel': channel,
            'time': time.time()
        })
        if data and self.gateway_write:
            self.gateway_write(data, channel)
        return data

    def on_send(self, data, channel=None):
        self.history.append({
            'direction': 'input',
            'data': data,
            'channel': channel,
            'time': time.time()
        })
        if data and self.target_write:
            self.target_write(data, channel)
        elif not data and self.target_write_eof:
            self.target_write_eof(channel)
        return data

    def on_exit(self):
        if self.exited.done():
            return
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
        if self.gateway_close:
            self.gateway_close()
        self.exited.set_result(data)
        return data
