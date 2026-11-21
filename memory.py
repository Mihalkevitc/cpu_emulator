from architecture import RAM_SIZE


class Memory:
    """Единая байтовая память для команд и данных."""
    def __init__(self, image=b''):
        self.data = bytearray(RAM_SIZE)
        self._check(0, len(image))
        self.data[:len(image)] = image

    @staticmethod
    def _check(address, size):
        if not 0 <= address <= RAM_SIZE - size:
            raise ValueError(f'Доступ за границей ОЗУ по адресу 0x{address:04X}')

    def read(self, address, size=2):
        """Читает беззнаковое число в порядке от младшего байта к старшему."""
        self._check(address, size)
        return int.from_bytes(self.data[address:address + size], 'little')

    def write(self, address, value):
        """Записывает 16-битное слово по байтовому адресу."""
        self._check(address, 2)
        self.data[address:address + 2] = value.to_bytes(2, 'little')
