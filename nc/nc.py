import sys
import os
import socket
import selectors
import fcntl


def listen_server(host, port):
    server_socket = socket.socket()

    server_socket.bind((host, port))

    server_socket.listen(1)

    conn, address = server_socket.accept()

    selector = selectors.DefaultSelector()

    stdin_shutdown = False
    def stdin_callback(data):
        nonlocal stdin_shutdown
        if not data:
            conn.shutdown(socket.SHUT_WR)
            stdin_shutdown = True
        if not stdin_shutdown:
            conn.send(data)

    fl = fcntl.fcntl(sys.stdin.buffer.raw, fcntl.F_GETFL)
    fcntl.fcntl(sys.stdin.buffer.raw, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    selector.register(sys.stdin.buffer.raw, selectors.EVENT_READ, stdin_callback)

    conn_shutdown = False
    def conn_callback(data):
        nonlocal conn_shutdown
        if not data:
            conn_shutdown = True
        if not conn_shutdown:
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()

    fl = fcntl.fcntl(conn, fcntl.F_GETFL)
    fcntl.fcntl(conn, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    selector.register(conn, selectors.EVENT_READ, conn_callback)

    try:
        while selector.get_map():
            for key, mask in selector.select():
                callback = key.data
                fileobj = key.fileobj
                if type(fileobj) is socket.socket:
                    data = fileobj.recv(65535)
                else:
                    data = fileobj.read()
                callback(data)
                if stdin_shutdown and conn_shutdown:
                    return

    except KeyboardInterrupt:
        pass


def connect_server(host, port):
    conn = socket.socket()

    conn.connect((host, port))

    selector = selectors.DefaultSelector()

    stdin_shutdown = False
    def stdin_callback(data):
        nonlocal stdin_shutdown
        if not data:
            conn.shutdown(socket.SHUT_WR)
            stdin_shutdown = True
        if not stdin_shutdown:
            conn.send(data)

    fl = fcntl.fcntl(sys.stdin.buffer.raw, fcntl.F_GETFL)
    fcntl.fcntl(sys.stdin.buffer.raw, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    selector.register(sys.stdin.buffer.raw, selectors.EVENT_READ, stdin_callback)

    conn_shutdown = False
    def conn_callback(data):
        nonlocal conn_shutdown
        if not data:
            conn_shutdown = True
        if not conn_shutdown:
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()

    fl = fcntl.fcntl(conn, fcntl.F_GETFL)
    fcntl.fcntl(conn, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    selector.register(conn, selectors.EVENT_READ, conn_callback)

    try:
        while selector.get_map():
            for key, mask in selector.select():
                callback = key.data
                fileobj = key.fileobj
                if type(fileobj) is socket.socket:
                    data = fileobj.recv(65535)
                else:
                    data = fileobj.read()
                callback(data)
                if stdin_shutdown and conn_shutdown:
                    return

    except KeyboardInterrupt:
        pass


def main():
    host = sys.argv[2]
    port = int(sys.argv[3])

    if sys.argv[1] == '-s':
        listen_server(host, port)
    elif sys.argv[1] == '-c':
        connect_server(host, port)


if __name__ == '__main__':
    main()
