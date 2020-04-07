
class PwnstarTerminal {
    constructor(name, input, outputs, tty, select) {
        this.name = name;
        this.input = input;
        this.outputs = outputs;
        this.tty = tty;

        this.writable = true;

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
    var buffer = '';

    function onKey(e) {
        if (terminal.input === null)
            return;
        if (!terminal.writable)
            return;

        const modifier = 0 |
              (e.domEvent.ctrlKey && 1) |
              (e.domEvent.altKey && 2) |
              (e.domEvent.metaKey && 4);

        console.log(modifier);
        console.log(e.domEvent.key);

        if (e.domEvent.key === 'Enter' && !modifier) {
            buffer += '\n';
            socket.send(JSON.stringify({
                'data': buffer,
                'channel': terminal.input
            }));
            buffer = '';
            terminal.xterm.write('\r\n');
        }
        else if (e.domEvent.key === 'Backspace' && !modifier) {
            // Do not delete the prompt
            if (buffer) {
                buffer = buffer.slice(0, buffer.length - 1);
                terminal.xterm.write('\b \b');
            }
        }
        else if (e.domEvent.key === 'd' && modifier === 1 && !buffer) {
            socket.send(JSON.stringify({
                'data': buffer,
                'channel': terminal.input
            }));
        }
        else if (e.domEvent.key === 'c' && modifier === 1) {
            socket.send(JSON.stringify({
                'signal': 'kill',
                'channel': terminal.input
            }));
        }
        else if (e.domEvent.key === e.key && !modifier) {
            buffer += e.key;
            terminal.xterm.write('\033[0;33m' + e.key + '\033[0m');
        }
    }

    function onmessage(e) {
        const decoder = new TextDecoder('utf-8');
        const message = JSON.parse(decoder.decode(e.data));

        if (!message.data && !message.channel) {
            return;
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
                terminal.xterm.write('\033[0;33m' + buffer[i] + '\033[0m');
            }
        }
    }

    return [onKey, onmessage];
}

function ttyHandlers(terminal, socket) {
    function onData(e) {
        if (socket.readyState == 1) {
            console.log(JSON.stringify(e));
            socket.send(JSON.stringify({
                'data': e,
                'channel': terminal.input
            }));
        }
    }

    function onmessage(e) {
        const decoder = new TextDecoder('utf-8');
        const message = JSON.parse(decoder.decode(e.data));

        if (!message.data && !message.channel) {
            return;
        }

        if (!terminal.outputs.includes(message.channel)) {
            return;
        }

        terminal.xterm.write(typeof message.data === 'string' ? message.data : new Uint8Array(message.data));
    }

    return [onData, onmessage];
}

$(function () {
    const search = new URLSearchParams(window.location.search);

    const baseUrl = window.location.origin + window.location.pathname;
    const infoUrl = baseUrl + (baseUrl.endsWith('/') ? '' : '/') + 'info' + window.location.search;
    const wsUrl = baseUrl + (baseUrl.endsWith('/') ? '' : '/') + 'ws' + window.location.search;

    $.getJSON(infoUrl, (response) => {
        const channels = response.channels;

        var url = new URL(wsUrl);
        url.protocol = url.protocol.replace('http', 'ws');

        var socket = new WebSocket(url);
        socket.binaryType = 'arraybuffer';

        socket.onclose = (e) => {
            window.terminals.forEach((t) => {
                t.writable = false;
            });
            $('.xterm-cursor-layer').hide();

            if (search.get('oneshot') === null) {
                $('.pwnstar-terminal').css('opacity', '0.5');
                $('.pwnstar-modal').removeClass('loader');
                $('.pwnstar-modal').addClass('redo');
                $('.pwnstar-modal').show(1000);
                $('.pwnstar-modal').click(() => {
                    window.location.reload();
                })
            }
        }

        socket.onmessage = (e) => {
            const decoder = new TextDecoder('utf-8');
            const message = JSON.parse(decoder.decode(e.data));

            if (message.status === 'ready') {
                $('.loader').hide(1000);
                $('.pwnstar-kill').click((e) => {
                    socket.send(JSON.stringify({
                        'signal': 'kill'
                    }));
                });
            }
            else if (message.status === 'close') {
                if (search.get('annotate') === null) {
                    socket.close();
                }
                else {
                    $('#annotateModal').on('shown.bs.modal', function () {
                        $('#annotation').focus();
                    });
                    $('#annotate').click(() => {
                        $('#annotateModal').modal('hide');
                        socket.send(JSON.stringify({
                            'data': $('#annotation').val(),
                            'channel': 'annotation'
                        }));
                        socket.close();
                    });
                    $('#annotateModal').modal();
                }
            }
        }

        var selected = false;

        var initialInput = atob(window.location.hash.substring(1));
        if (initialInput) {
            initialInput = JSON.parse(initialInput);
        }
        else {
            initialInput = {};
        }

        window.terminals = [];

        channels.forEach((channel) => {
            const name = channel[0];
            const input = channel[1];
            const outputs = channel[2];
            const tty = channel[3];

            const terminal = new PwnstarTerminal(name, input, outputs, tty);
            window.terminals.push(terminal);

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

                    const decoder = new TextDecoder('utf-8');
                    const message = JSON.parse(decoder.decode(e.data));

                    if (message.status === 'ready') {
                        if (input in initialInput) {
                            initialInput[input].split('').forEach((c) => {
                                onKey({
                                    key: c,
                                    domEvent: new KeyboardEvent('keydown', {'key': c != '\n' ? c : 'Enter'})
                                });
                            });
                        }
                    }

                    onmessage(e);
                };
            }

            else {
                const handlers = ttyHandlers(terminal, socket);
                const onData = handlers[0];
                const onmessage = handlers[1];

                terminal.xterm.onData(onData);

                const prevOnmessage = socket.onmessage;
                socket.onmessage = (e) => {
                    if (prevOnmessage) {
                        prevOnmessage(e);
                    }
                    onmessage(e);
                };
            }
        });
    });
});
