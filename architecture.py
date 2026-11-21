from dataclasses import dataclass
from enum import IntEnum

# Позиция имени в кортеже совпадает с номером регистра в машинной команде.
REGISTERS = (
    'AX', 'BX', 'CX', 'DX', 'SI', 'DI', 'BP', 'SP',
    *(f'R{i}' for i in range(8, 16)),
)
MASK     = 0xFFFF   # Младшие 16 бит результата или адреса.
RAM_SIZE = 1 << 16  # Один байт на каждый адрес от 0x0000 до 0xFFFF.


class Op(IntEnum):
    """Коды операций в старших четырёх битах команды."""

    NOP  = 0   # Пустая операция.
    MOV  = 1   # Копирование значения.
    XCHG = 2   # Обмен значениями.
    ADD  = 3   # Сложение.
    ADC  = 4   # Сложение с входным переносом CF.
    SUB  = 5   # Вычитание.
    CMP  = 6   # Вычитание с обновлением только флагов.
    MUL  = 7   # Беззнаковое умножение AX на регистр, результат в DX:AX.
    INC  = 8   # Прибавление единицы.
    DEC  = 9   # Вычитание единицы.
    JMP  = 10  # Безусловный переход.
    JE   = 11  # Переход при ZF = 1.
    JNE  = 12  # Переход при ZF = 0.
    JB   = 13  # Беззнаковое «меньше», CF = 1.
    JAE  = 14  # Беззнаковое «больше или равно», CF = 0.
    HALT = 15  # Остановка процессора.


class Mode(IntEnum):
    """Двухбитные коды адресации в полях MODE1 и MODE2."""

    REG      = 0  # AX: значение регистра.
    IMM      = 1  # 42: значение из PAYLOAD.
    DIRECT   = 2  # [42]: слово ОЗУ по адресу из PAYLOAD.
    INDIRECT = 3  # [SI]: слово ОЗУ по адресу из регистра.


R, I, D, X = Mode.REG, Mode.IMM, Mode.DIRECT, Mode.INDIRECT
MEM      = (D, X)                                # Операнды в ОЗУ.
WRITABLE = (R, D, X)                             # Допустимые назначения записи.
JUMPS    = (Op.JMP, Op.JE, Op.JNE, Op.JB, Op.JAE)  # Переходы с абсолютным адресом.

# Для каждого операнда указан набор режимов. Порядок соответствует записи команды.
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
        """Проверяет операнды и упаковывает команду в 32-битное слово."""
        allowed = MODES[self.op]
        if len(self.operands) != len(allowed):
            raise ValueError(f'{self.op.name}: ожидается операндов: {len(allowed)}')
        # PAYLOAD общий для обоих операндов, а обращение к ОЗУ допускается одно.
        modes = [mode for mode, _ in self.operands]
        if sum(mode in (I, D) for mode in modes) > 1 or sum(mode in MEM for mode in modes) > 1:
            raise ValueError('В команде допустим один операнд памяти и один PAYLOAD')

        # Поля OP1 и OP2 начинаются с битов 22 и 16, поля MODE идут сразу над ними.
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
        """Извлекает операнды из машинного слова и проверяет кодировку."""
        op = Op(word >> 28)
        operands = []
        for shift in (22, 16)[:len(MODES[op])]:
            mode = Mode((word >> (shift + 4)) & 3)
            value = (word >> shift) & 15 if mode in (R, X) else word & MASK
            operands.append((mode, value))
        instruction = cls(op, tuple(operands))
        # Повторная упаковка проверяет режимы и нули в незадействованных полях.
        if instruction.encode() != word:
            raise ValueError(f'Некорректная кодировка 0x{word:08X}')
        return instruction

    def __str__(self):
        rendered = []
        for mode, value in self.operands:
            name = REGISTERS[value] if mode in (R, X) else f'0x{value:04X}'
            rendered.append(f'[{name}]' if mode in MEM else name)
        return ' '.join(filter(None, (self.op.name, ', '.join(rendered))))
