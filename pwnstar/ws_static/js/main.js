
class PwnstarTerminal {
    constructor(name, input, outputs, tty, select) {
        this.name = name;
        this.input = input;
        this.outputs = outputs;
        this.tty = tty;

        this.tab = $('<div>').attr('class', 'pwnstar-tab').text(name);
        this.terminal = $('<div>').attr('class', 'pwnstar-terminal');

        this.tab.click(() => {
            this.select();
        });

        $('.pwnstar-tabs').append(this.tab);
        $('.pwnstar-terminals').append(this.terminal);

        this.xterm = new window.Terminal();
        this.xterm.open(this.terminal[0]);

        function resize(terminal) {
            const MINIMUM_COLS = 2;
            const MINIMUM_ROWS = 1;

            const core = terminal._core;

            const parentElementStyle = window.getComputedStyle(terminal.element.parentElement);
            const parentElementHeight = parseInt(parentElementStyle.getPropertyValue('height'));
            const parentElementWidth = Math.max(0, parseInt(parentElementStyle.getPropertyValue('width')));
            const elementStyle = window.getComputedStyle(terminal.element);
            const elementPadding = {
                top: parseInt(elementStyle.getPropertyValue('padding-top')),
                bottom: parseInt(elementStyle.getPropertyValue('padding-bottom')),
                right: parseInt(elementStyle.getPropertyValue('padding-right')),
                left: parseInt(elementStyle.getPropertyValue('padding-left'))
            };
            const elementPaddingVer = elementPadding.top + elementPadding.bottom;
            const elementPaddingHor = elementPadding.right + elementPadding.left;
            const availableHeight = parentElementHeight - elementPaddingVer;
            const availableWidth = parentElementWidth - elementPaddingHor - core.viewport.scrollBarWidth;
            const geometry = {
                cols: Math.max(MINIMUM_COLS, Math.floor(availableWidth / core._renderService.dimensions.actualCellWidth)),
                rows: Math.max(MINIMUM_ROWS, Math.floor(availableHeight / core._renderService.dimensions.actualCellHeight))
            };

            core._renderService.clear();
            terminal.resize(geometry.cols, geometry.rows);
        }

        resize(this.xterm);
        $(window).resize(() => resize(this.xterm));

        if (select) {
            this.select();
        }
    }

    select() {
        $('.pwnstar-tab').css('background-color', '');
        $('.pwnstar-terminal').css('display', 'none');
        $('.pwnstar-terminal').css('visibility', '');

        this.tab.css('background-color', 'lightgray');
        this.terminal.css('display', 'block');
        this.terminal.css('visibility', 'visible');
        this.xterm.focus();
    }
}

function nonttyHandlers(terminal, socket) {
    var buffer = "";

    function onKey(e) {
        if (terminal.input === null) {
            return;
        }

        const printable = !e.domEvent.altKey && !e.domEvent.altGraphKey && !e.domEvent.ctrlKey && !e.domEvent.metaKey;

        if (e.domEvent.keyCode === 13) {
            buffer += '\n';
            socket.send(JSON.stringify({
                "data": buffer,
                "channel": terminal.input
            }));
            buffer = "";
            terminal.xterm.write('\r\n');
        }
        else if (e.domEvent.keyCode === 8) {
            // Do not delete the prompt
            if (buffer) {
                buffer = buffer.slice(0, buffer.length - 1);
                terminal.xterm.write('\b \b');
            }
        }
        else if (printable) {
            buffer += e.key;
            terminal.xterm.write(e.key);
        }
    }

    function onmessage(e) {
        var message = null;

        if (typeof data !== 'string') {
            var enc = new TextDecoder("utf-8");
            message = JSON.parse(enc.decode(event.data));
        }
        else {
            message = JSON.parse(event.data);
        }

        if (!terminal.outputs.includes(message.channel)) {
            return;
        }

        if (buffer) {
            for (var i = 0; i < buffer.length; i++) {
                terminal.xterm.write('\b \b');
            }
        }

        message.data = message.data.replace(/\n/g, '\n\r');

        if (message.channel === 2) {
            message.data = '\033[0;31m' + message.data + '\033[0m';
        }

        terminal.xterm.write(message.data);

        if (buffer) {
            for (var i = 0; i < buffer.length; i++) {
                terminal.xterm.write(buffer[i]);
            }
        }
    }

    return [onKey, onmessage];
}

$(function () {
    $.getJSON(window.location.href + '/info', (response) => {
        const tty = response.tty;
        const channels = response.channels;

        var url = new URL(window.location.href + '/ws');
        url.protocol = url.protocol.replace('http', 'ws');

        var socket = new WebSocket(url);
        socket.binaryType = 'arraybuffer';

        socket.onclose = (event) => {
            jQuery('.pwnstar-terminal').css('opacity', '0.5');
        }

        var selected = false;

        channels.forEach((channel) => {
            const name = channel[0];
            const input = channel[1];
            const outputs = channel[2];
            const tty = channel[3];

            const terminal = new PwnstarTerminal(name, input, outputs, tty);

            if (!selected) {
                terminal.select();
                selected = true;
            }

            if (!tty) {
                const handlers = nonttyHandlers(terminal, socket);
                const onKey = handlers[0];
                const onmessage = handlers[1];

                terminal.xterm.onKey(onKey);

                const prevOnmessage = socket.onmessage;
                socket.onmessage = (e) => {
                    if (prevOnmessage) {
                        prevOnmessage(e);
                    }
                    onmessage(e);
                };
            }

            else {
                // TODO: hasn't been upgraded for multichannel yet
                terminal.xterm.onData((data) => {
                    if (socket.readyState == 1) {
                        socket.send(data);
                    }
                });

                socket.onmessage = (event) => {
                    const data = event.data;
                    terminal.xterm.write(typeof data === 'string' ? data : new Uint8Array(data));
                };
            }
        });
    });
});
