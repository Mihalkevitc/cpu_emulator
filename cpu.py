from dataclasses import dataclass

from architecture import D, I, R, JUMPS, MASK, Instruction, Op
from memory import Memory


@dataclass(frozen=True)
class Step:
    address: int
    ir: int
    instruction: Instruction
    pc: int
    registers: tuple[int, ...]
    zf: bool
    cf: bool
    sf: bool
    write: tuple[int, int, int] | None


class CPU:
    def __init__(self, image=b''):
        self.memory = Memory(image)
        self.registers = [0] * 16
        self.pc = self.ir = 0
        self.zf = self.cf = self.sf = self.halted = False

    def _address(self, mode, value):
        """Возвращает байтовый адрес прямого или косвенного операнда."""
        return value if mode == D else self.registers[value]

    def _read(self, operand):
        """Читает значение из инструкции, регистра или ОЗУ."""
        mode, value = operand
        if mode == I:
            return value
        if mode == R:
            return self.registers[value]
        return self.memory.read(self._address(mode, value))

    def _write(self, operand, value):
        """Записывает слово и возвращает сведения о записи в ОЗУ."""
        mode, index = operand
        if mode == R:
            self.registers[index] = value
            return None
        address = self._address(mode, index)
        before = self.memory.read(address)
        self.memory.write(address, value)
        return address, before, value

    def step(self):
        """Выполняет одну инструкцию и возвращает снимок состояния."""
        if self.halted:
            raise ValueError('Процессор остановлен')
        address = self.pc
        raw = self.memory.read(address, 4)
        instruction = Instruction.decode(raw)
        # Команда занимает четыре байта. Выполненный переход заменит этот адрес.
        next_pc = (address + 4) & MASK
        op, args = instruction.op, instruction.operands
        write = None
        if op == Op.HALT:
            self.halted = True
        elif op in JUMPS:
            take = {
                Op.JMP: True, Op.JE: self.zf, Op.JNE: not self.zf,
                Op.JB: self.cf, Op.JAE: not self.cf,
            }
            if take[op]:
                next_pc = args[0][1]
        elif op == Op.MOV:
            write = self._write(args[0], self._read(args[1]))
        elif op == Op.XCHG:
            left, right = map(self._read, args)
            # Сначала записываем память, пока регистр-указатель ещё не изменён.
            first, second = (1, 0) if args[0][0] == R else (0, 1)
            values = (right, left)
            write = self._write(args[first], values[first])
            self._write(args[second], values[second])
        elif op == Op.MUL:
            product = self.registers[0] * self._read(args[0])
            # Делим 32-битное произведение между AX и DX.
            self.registers[0] = product & MASK
            self.registers[3] = product >> 16
            self.cf = bool(self.registers[3])
            self.zf = product == 0
            self.sf = bool(product & 0x80000000)
        elif op != Op.NOP:
            left = self._read(args[0])
            right = self._read(args[1]) if len(args) == 2 else 1
            if op in (Op.SUB, Op.CMP, Op.DEC):
                total = left - right
            else:
                total = left + right + (self.cf if op == Op.ADC else 0)
            # Сохраняем младшее слово, перенос или заём определяем по полной сумме.
            result = total & MASK
            self.cf = not 0 <= total <= MASK
            self.zf = result == 0
            self.sf = bool(result & 0x8000)
            if op != Op.CMP:
                self._write(args[0], result)

        self.pc, self.ir = next_pc, raw
        return Step(address, raw, instruction, next_pc, tuple(self.registers),
                    self.zf, self.cf, self.sf, write)

    def run(self, limit=10_000):
        """Выдаёт снимки до HALT и прерывает выполнение при исчерпании лимита."""
        for _ in range(limit):
            if self.halted:
                break
            yield self.step()
        if not self.halted:
            raise ValueError(f'Достигнут лимит инструкций ({limit})')
