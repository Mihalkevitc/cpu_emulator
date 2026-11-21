import re
from dataclasses import dataclass

from architecture import D, I, R, X, RAM_SIZE, REGISTERS, Instruction, Op

LABEL = re.compile(r'[A-Z_][A-Z_0-9]*')


@dataclass
class Program:
    image: bytes
    symbols: dict[str, int]
    listing: list[tuple[int, bytes, str]]


def number(token, symbols):
    token = token.strip()
    match = re.fullmatch(r'([A-Z_][A-Z_0-9]*)(?:\s*([+-])\s*(0X[0-9A-F]+|[0-9]+))?', token)
    if match:
        label, sign, offset = match.groups()
        if label not in symbols:
            raise ValueError(f'Неизвестная метка: {label}')
        return symbols[label] + (number(sign + offset, {}) if sign else 0)
    return int(token, 16 if token.lstrip('+-').startswith('0X') else 10)


def operand(token, symbols):
    token = token.strip()
    indirect = token.startswith('[') and token.endswith(']')
    if indirect:
        token = token[1:-1].strip()
    if token in REGISTERS:
        return (X if indirect else R), REGISTERS.index(token)
    return (D if indirect else I), number(token, symbols)


def assemble(source):
    symbols, lines = {}, []
    address = 0
    # Первый проход определяет адреса, в том числе для ссылок вперёд.
    for line_no, original in enumerate(source.splitlines(), 1):
        line = original.partition(';')[0].strip().upper()
        if ':' in line:
            name, line = (part.strip() for part in line.split(':', 1))
            if not LABEL.fullmatch(name) or name in symbols or name in REGISTERS:
                raise ValueError(f'Строка {line_no}: неверная или повторная метка {name}')
            symbols[name] = address
        if not line:
            continue
        fields = line.split(maxsplit=1)
        name = fields[0]
        args = fields[1].split(',') if len(fields) == 2 else []
        lines.append((line_no, address, name, args, original.strip()))
        address += 2 * len(args) if name == 'DW' else 4
        if address > RAM_SIZE:
            raise ValueError(f'Строка {line_no}: программа не помещается в ОЗУ')

    image, listing = bytearray(), []
    for line_no, address, name, args, original in lines:
        try:
            if name == 'DW':
                if not args:
                    raise ValueError('DW требует хотя бы одно значение')
                encoded = b''.join(number(arg, symbols).to_bytes(2, 'little') for arg in args)
            else:
                if name not in Op.__members__:
                    raise ValueError(f'Неизвестная команда: {name}')
                instruction = Instruction(Op[name], tuple(operand(arg, symbols) for arg in args))
                encoded = instruction.encode().to_bytes(4, 'little')
        except (ValueError, OverflowError) as error:
            raise ValueError(f'Строка {line_no}: {error}') from error
        image.extend(encoded)
        listing.append((address, encoded, original))
    return Program(bytes(image), symbols, listing)
