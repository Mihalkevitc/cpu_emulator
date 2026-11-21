from dataclasses import dataclass
from enum import IntEnum

REGISTERS = ('AX', 'BX', 'CX', 'DX', 'SI', 'DI', 'BP', 'SP', *(f'R{i}' for i in range(8, 16)))
MASK = 0xFFFF
RAM_SIZE = 1 << 16


class Op(IntEnum):
    NOP = 0
    MOV = 1
    XCHG = 2
    ADD = 3
    ADC = 4
    SUB = 5
    CMP = 6
    MUL = 7
    INC = 8
    DEC = 9
    JMP = 10
    JE = 11
    JNE = 12
    JB = 13
    JAE = 14
    HALT = 15


class Mode(IntEnum):
    REG = 0
    IMM = 1
    DIRECT = 2
    INDIRECT = 3


R, I, D, X = Mode
MEM = (D, X)
WRITABLE = (R, D, X)
JUMPS = (Op.JMP, Op.JE, Op.JNE, Op.JB, Op.JAE)
MODES = {
    Op.NOP: (), Op.HALT: (),
    Op.MOV: (WRITABLE, tuple(Mode)),
    Op.XCHG: (WRITABLE, WRITABLE),
    Op.MUL: ((R,),), Op.INC: ((R,),), Op.DEC: ((R,),),
    **{op: ((R,), (R, I)) for op in (Op.ADD, Op.ADC, Op.SUB, Op.CMP)},
    **{op: ((I,),) for op in JUMPS},
}


@dataclass(frozen=True)
class Instruction:
    op: Op
    operands: tuple[tuple[Mode, int], ...] = ()

    def encode(self):
        allowed = MODES[self.op]
        if len(self.operands) != len(allowed):
            raise ValueError(f'{self.op.name}: ожидается операндов: {len(allowed)}')
        modes = [mode for mode, _ in self.operands]
        if sum(mode in (I, D) for mode in modes) > 1 or sum(mode in MEM for mode in modes) > 1:
            raise ValueError('В команде допустим один операнд памяти и один PAYLOAD')

        word = self.op << 28
        for (mode, value), options, shift in zip(self.operands, allowed, (22, 16)):
            if mode not in options:
                raise ValueError(f'{self.op.name}: недопустимый режим {mode.name}')
            limit = 15 if mode in (R, X) else MASK
            if not 0 <= value <= limit:
                raise ValueError(f'Операнд вне диапазона: {value}')
            word |= mode << (shift + 4)
            word |= value << shift if mode in (R, X) else value
        return word

    @classmethod
    def decode(cls, word):
        op = Op(word >> 28)
        operands = []
        for shift in (22, 16)[:len(MODES[op])]:
            mode = Mode((word >> (shift + 4)) & 3)
            value = (word >> shift) & 15 if mode in (R, X) else word & MASK
            operands.append((mode, value))
        instruction = cls(op, tuple(operands))
        if instruction.encode() != word:
            raise ValueError(f'Некорректная кодировка 0x{word:08X}')
        return instruction

    def __str__(self):
        rendered = []
        for mode, value in self.operands:
            name = REGISTERS[value] if mode in (R, X) else f'0x{value:04X}'
            rendered.append(f'[{name}]' if mode in MEM else name)
        return ' '.join(filter(None, (self.op.name, ', '.join(rendered))))
