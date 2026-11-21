import unittest
from pathlib import Path

from assembler import assemble
from cpu import CPU

PROGRAMS = Path(__file__).resolve().parents[1] / 'programs'


def execute(source):
    program = assemble(source)
    cpu = CPU(program.image)
    return program, cpu, list(cpu.run())


class EmulatorTest(unittest.TestCase):
    def test_maximum(self):
        source = (PROGRAMS / 'find_max.asm').read_text(encoding='utf-8')
        for data, expected in [('6, 12, 65535, 7, 1024, 3, 90', 65535), ('1, 42', 42)]:
            with self.subTest(data=data):
                program, cpu, _ = execute(source.replace('6, 12, 65535, 7, 1024, 3, 90', data))
                self.assertEqual(cpu.memory.read(program.symbols['MAX_RESULT']), expected)

    def test_convolution(self):
        source = (PROGRAMS / 'convolution.asm').read_text(encoding='utf-8')
        program, cpu, steps = execute(source)
        self.assertEqual(cpu.memory.read(program.symbols['RESULT'], 6), 6 * 65535**2)
        self.assertEqual(cpu.registers[8:11], [6, 0xFFF4, 5])
        product = next(step for step in steps if step.instruction.op.name == 'MUL')
        self.assertEqual((product.registers[3], product.registers[0]), (0xFFFE, 1))

    def test_carry_and_branch(self):
        _, cpu, steps = execute('MOV AX, 65535\nADD AX, 1\nADC BX, 0\n'
                                'CMP AX, BX\nJB DONE\nMOV CX, 99\nDONE: HALT')
        self.assertTrue(steps[1].cf and steps[1].zf)
        self.assertEqual(cpu.registers[:3], [0, 1, 0])
        self.assertEqual(steps[4].pc, steps[5].address)

    def test_exchange_with_pointer_alias(self):
        program, cpu, steps = execute('MOV SI, DATA\nXCHG SI, [SI]\nHALT\nDATA: DW 42')
        address = program.symbols['DATA']
        self.assertEqual(steps[1].write, (address, 42, address))
        self.assertEqual(cpu.registers[4], 42)

    def test_rejects_unsupported_operands(self):
        for source in ('MOV [100], 1', 'ADD AX, [SI]', 'JMP UNKNOWN', 'DW 65536'):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, '1:'):
                assemble(source)

    def test_instruction_limit(self):
        with self.assertRaisesRegex(ValueError, '2'):
            execute_program = CPU(assemble('JMP 0').image)
            list(execute_program.run(2))
