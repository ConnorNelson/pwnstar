$(function () {
    var terminal = new window.Terminal();
    terminal.open($('#terminal')[0]);

    function resize() {
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

        console.log(geometry);
    }

    resize();
    $(window).resize(resize);

    var url = new URL('/ws', window.location.href);
    url.protocol = url.protocol.replace('http', 'ws');

    var socket = new WebSocket(url);
    socket.binaryType = 'arraybuffer';

    $.getJSON('/tty', (tty) => {
        if (tty) {
            terminal.onData((data) => {
                if (socket.readyState == 1) {
                    socket.send(data);
                }
            });

            socket.onmessage = (event) => {
                const data = event.data;
                terminal.write(typeof data === 'string' ? data : new Uint8Array(data));
            };

            socket.onclose = (event) => {
                jQuery('#terminal').css('opacity', '0.5');
            };
        }
        else {
            var buffer = "";

            terminal.onKey((e) => {
                const printable = !e.domEvent.altKey && !e.domEvent.altGraphKey && !e.domEvent.ctrlKey && !e.domEvent.metaKey;

                if (e.domEvent.keyCode === 13) {
                    buffer += '\n';
                    socket.send(buffer);
                    console.log(buffer);
                    buffer = "";
                    terminal.write('\r\n');
                }
                else if (e.domEvent.keyCode === 8) {
                    // Do not delete the prompt
                    if (buffer) {
                        buffer = buffer.slice(0, buffer.length - 1);
                        terminal.write('\b \b');
                    }
                }
                else if (printable) {
                    buffer += e.key;
                    terminal.write(e.key);
                }
            });

            socket.onmessage = (event) => {
                var data = event.data;

                if (buffer) {
                    for (var i = 0; i < buffer.length; i++) {
                        terminal.write('\b \b');
                    }
                }

                if (typeof data !== 'string') {
                    var enc = new TextDecoder("utf-8");
                    data = enc.decode(event.data);
                }

                data = data.replace(/\n/g, '\n\r');
                terminal.write(data);

                if (buffer) {
                    for (var i = 0; i < buffer.length; i++) {
                        terminal.write(buffer[i]);
                    }
                }
            };

            socket.onclose = (event) => {
                jQuery('#terminal').css('opacity', '0.5');
            };
        }
    });


    // term.writeln("Hello world!");
    // term.writeln("This is a test!");
    // term.writeUtf8("\u001b]0;IPython: ire/leaker\u0007Python 3.8.0 (v3.8.0:fa919fdf25, Oct 14 2019, 10:23:27) \nType 'copyright', 'credits' or 'license' for more information\nIPython 7.8.0 -- An enhanced Interactive Python. Type '?' for help.\n\nIn [1]:".replace(/\n/g, '\n\r'));

    // term.onKey(e => {
    //     term.write(e.key + '\n');
    // });


    // function runFakeTerminal() {
    //     if (term._initialized) {
    //         return;
    //     }

    //     term._initialized = true;

    //     term.prompt = () => {
    //         term.write('\r\n$ ');
    //     };

    //     term.writeln('Welcome to xterm.js');
    //     term.writeln('This is a local terminal emulation, without a real terminal in the back-end.');
    //     term.writeln('Type some keys and commands to play around.');
    //     term.writeln('');
    //     prompt(term);

    //     term.onKey(e => {
    //         const printable = !e.domEvent.altKey && !e.domEvent.altGraphKey && !e.domEvent.ctrlKey && !e.domEvent.metaKey;

    //         if (e.domEvent.keyCode === 13) {
    //             prompt(term);
    //         } else if (e.domEvent.keyCode === 8) {
    //             // Do not delete the prompt
    //             if (term._core.buffer.x > 2) {
    //                 term.write('\b \b');
    //             }
    //         } else if (printable) {
    //             term.write(e.key);
    //         }
    //     });
    // }

    // function prompt(term) {
    //   term.write('\r\n$ ');
    // }
    // runFakeTerminal();
});

// $(function () {
//     var webSocket = new WebSocket('ws://localhost:4241/');

//     console.log(webSocket);

//     webSocket.onmessage = function (event) {
//         var reader = new FileReader();
//         reader.onload = function(event) {
//             var tr = $('<tr>');
//             tr.append($('<td>').text('output'));
//             tr.append($('<td>').append($('<pre>').text(event.target.result)));
//             $('#table > tbody > tr:last').after(tr);
//         };
//         reader.readAsText(event.data);
//     }


//     $('#submit').on('click', () => {
//         webSocket.send($('#input').val() + '\n');

//         var tr = $('<tr>');
//         tr.append($('<td>').text('input'));
//         tr.append($('<td>').text($('#input').val()));
//         $('#table > tbody > tr:last').after(tr);
//     });
// });
