"""Локальный интерфейс к ассемблеру и процессору."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import webbrowser

from architecture import RAM_SIZE, REGISTERS
from assembler import assemble
from cpu import CPU

ROOT = Path(__file__).resolve().parent
BATCH_SIZE = 64  # Между пакетами браузер обновляет экран и принимает команды.
RUN_LIMIT = 10_000
PAGE_SIZE = 128
FILES = {
    '/': ('ui/index.html', 'text/html'),
    '/style.css': ('ui/style.css', 'text/css'),
    '/app.js': ('ui/app.js', 'text/javascript'),
    '/maximum.asm': ('programs/find_max.asm', 'text/plain'),
    '/convolution.asm': ('programs/convolution.asm', 'text/plain'),
}


class Session:
    """Хранит состояние загруженной программы в пределах локального сеанса."""

    def __init__(self):
        self.cpu = CPU()
        self.symbols = {}
        self.loaded = False
        self.count = 0

    def update(self, request):
        """Выполняет действие и возвращает состояние и страницу ОЗУ."""
        action = request['action']
        address = request['address']
        if type(address) is not int or not 0 <= address < RAM_SIZE:
            raise ValueError('Адрес ОЗУ должен быть от 0000 до FFFF')
        trace, error = [], None
        if action == 'load':
            source = request['source']
            if not isinstance(source, str) or not source.strip():
                raise ValueError('Введите или выберите ассемблерную программу')
            program = assemble(source.removeprefix('\ufeff'))
            if not program.image:
                raise ValueError('Программа не содержит команд или данных')
            self.cpu = CPU(program.image)
            self.symbols = program.symbols
            self.loaded = True
            self.count = 0
        elif action in ('step', 'run') and self.loaded:
            for _ in range(1 if action == 'step' else BATCH_SIZE):
                if self.cpu.halted:
                    break
                if action == 'run' and self.count >= RUN_LIMIT:
                    error = f'Достигнут лимит автоматического запуска ({RUN_LIMIT})'
                    break
                try:
                    step = self.cpu.step()
                except ValueError as failure:
                    error = str(failure)
                    break
                self.count += 1
                trace.append({
                    'number': self.count, 'address': step.address, 'ir': step.ir,
                    'command': str(step.instruction), 'pc': step.pc,
                    'registers': step.registers, 'flags': [step.zf, step.cf, step.sf],
                    'write': step.write,
                })
        elif action != 'memory':
            raise ValueError('Сначала загрузите программу')

        start = address // PAGE_SIZE * PAGE_SIZE
        return {
            'loaded': self.loaded, 'halted': self.cpu.halted, 'count': self.count,
            'register_names': REGISTERS, 'registers': self.cpu.registers,
            'pc': self.cpu.pc, 'ir': self.cpu.ir,
            'flags': [self.cpu.zf, self.cpu.cf, self.cpu.sf],
            'trace': trace, 'error': error, 'symbols': self.symbols,
            'memory_start': start, 'memory': list(self.cpu.memory.data[start:start + PAGE_SIZE]),
        }


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, content_type, data):
        self.send_response(status)
        self.send_header('Content-Type', content_type + '; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self.local_host():
            self.send_error(403)
            return
        if self.path not in FILES:
            self.send_error(404)
            return
        path, content_type = FILES[self.path]
        self.reply(200, content_type, (ROOT / path).read_bytes())

    def do_POST(self):
        if self.path != '/api':
            self.send_error(404)
            return
        origin = self.headers.get('Origin')
        if not self.local_host() or self.headers.get_content_type() != 'application/json' or (
            origin and origin != f'http://127.0.0.1:{self.server.server_port}'
        ):
            self.send_error(403)
            return
        try:
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length <= 1_048_576:  # Ограничиваем размер текста запроса.
                raise ValueError('Допустимый размер запроса — до 1 МиБ')
            request = json.loads(self.rfile.read(length))
            result = self.server.session.update(request)
            status = 200
        except (ValueError, KeyError, TypeError) as failure:
            status, result = 400, {'error': str(failure)}
        self.reply(status, 'application/json', json.dumps(result, ensure_ascii=False).encode('utf-8'))

    def local_host(self):
        return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    with HTTPServer(('127.0.0.1', args.port), Handler) as server:
        server.session = Session()
        url = f'http://127.0.0.1:{server.server_port}'
        print(f'Эмулятор: {url} (Ctrl+C — выход)', flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
