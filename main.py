import argparse
from pathlib import Path

from architecture import REGISTERS
from assembler import assemble
from cpu import CPU


def print_step(step):
    print(f'{step.address:04X}  IR={step.ir:08X}  {step.instruction}  PC={step.pc:04X}')
    word = step.ir
    print(f'  OPCODE={word >> 28:X} MODE1={(word >> 26) & 3:02b} OP1={(word >> 22) & 15:X} '
          f'MODE2={(word >> 20) & 3:02b} OP2={(word >> 16) & 15:X} PAYLOAD={word & 0xFFFF:04X}')
    print('  ' + ' '.join(f'{name}={value:04X}' for name, value in zip(REGISTERS, step.registers)))
    print(f'  ZF={int(step.zf)} CF={int(step.cf)} SF={int(step.sf)}')
    if step.write is not None:
        address, before, after = step.write
        print(f'  ОЗУ[{address:04X}]: {before:04X} → {after:04X}')


def main():
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
        while not cpu.halted:
            if args.step and input('Enter — выполнить команду, q — выход: ').strip().lower() == 'q':
                return
            print_step(next(steps))
        if label:
            value = cpu.memory.read(program.symbols[label], 2 * args.words)
            print(f'{label} = {value} (0x{value:0{4 * args.words}X})')
    except (OSError, ValueError) as error:
        parser.exit(1, f'Ошибка: {error}\n')
    except (EOFError, KeyboardInterrupt):
        parser.exit(130, '\nВыполнение прервано.\n')


if __name__ == '__main__':
    main()
