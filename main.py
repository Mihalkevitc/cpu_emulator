import argparse
from pathlib import Path

from architecture import REGISTERS
from assembler import assemble
from cpu import CPU


def print_step(number, step, previous):
    """Выводит состояние после команды и отмечает изменения звёздочкой."""
    print(f'\nШаг {number:03} | {step.address:04X}  {step.instruction}')
    print(f'  IR: {step.ir:08X}    PC: {step.address:04X} → {step.pc:04X}')
    word = step.ir
    print('  OPCODE | MODE1 | OP1 | MODE2 | OP2 | PAYLOAD')
    print(f'       {word >> 28:X} |    {(word >> 26) & 3:02b} |   {(word >> 22) & 15:X} |'
          f'    {(word >> 20) & 3:02b} |   {(word >> 16) & 15:X} |    {word & 0xFFFF:04X}')

    print('  Регистры')
    old_registers = previous.registers if previous else (0,) * len(REGISTERS)
    for start in (0, 8):
        group = slice(start, start + 8)
        names = ' | '.join(f'{name:^5}' for name in REGISTERS[group])
        values = ' | '.join(
            f'{value:04X}{"*" if value != old else " "}'
            for value, old in zip(step.registers[group], old_registers[group])
        )
        print(f'  {names}\n  {values}')

    flags = ('zf', 'cf', 'sf')
    values = ' | '.join(
        f'{name.upper()} {int(getattr(step, name))}'
        f'{"*" if getattr(step, name) != getattr(previous, name, False) else " "}'
        for name in flags
    )
    print(f'  Флаги   {values}')
    if step.write is not None:
        address, before, after = step.write
        print(f'  ОЗУ[{address:04X}]: {before:04X} → {after:04X}')


def main():
    """Собирает программу и запускает выбранный режим консоли."""
    parser = argparse.ArgumentParser(description='Эмулятор процессора, вариант 10')
    parser.add_argument('source', type=Path, help='файл программы .asm')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--step', action='store_true', help='Enter выполняет одну команду')
    mode.add_argument('--listing', action='store_true', help='вывести листинг машинного кода')
    parser.add_argument('--limit', type=int, default=10_000, help='лимит команд')
    parser.add_argument('--result', metavar='МЕТКА', help='прочитать результат из ОЗУ')
    parser.add_argument('--words', type=int, choices=(1, 2, 3), default=1)
    args = parser.parse_args()

    try:
        program = assemble(args.source.read_text(encoding='utf-8-sig'))
        if args.listing:
            for address, encoded, source in program.listing:
                print(f'{address:04X}  {encoded.hex(" ").upper():<20}  {source}')
            return
        if args.limit < 1:
            raise ValueError('Лимит команд должен быть положительным')
        label = args.result.upper() if args.result else None
        if label and label not in program.symbols:
            raise ValueError(f'Неизвестная метка: {label}')
        cpu = CPU(program.image)
        steps = iter(cpu.run(args.limit))
        print('Адреса и регистры в hex; * - значение изменилось за шаг.')
        previous = None
        number = 0
        while not cpu.halted:
            if args.step and input('Enter - выполнить команду, q - выход: ').strip().lower() == 'q':
                return
            current = next(steps)
            number += 1
            print_step(number, current, previous)
            previous = current
        if label:
            value = cpu.memory.read(program.symbols[label], 2 * args.words)
            print(f'{label} = {value} (0x{value:0{4 * args.words}X})')
    except (OSError, ValueError) as error:
        parser.exit(1, f'Ошибка: {error}\n')
    except (EOFError, KeyboardInterrupt):
        parser.exit(130, '\nВыполнение прервано.\n')


if __name__ == '__main__':
    main()
