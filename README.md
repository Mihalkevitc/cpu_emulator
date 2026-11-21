# Эмулятор процессора. Вариант 10

Консольный эмулятор двухадресного процессора с архитектурой фон Неймана. Требуется Python 3.10 или новее, внешних зависимостей нет.

```powershell
# Поиск максимума, вывод результата MAX_RESULT
python main.py programs/find_max.asm --result MAX_RESULT

# Свёртка, 3 слова результата
python main.py programs/convolution.asm --result RESULT --words 3

# Пошаговый режим (Enter — команда, q — выход)
python main.py programs/find_max.asm --step

# Только листинг машинного кода
python main.py programs/convolution.asm --listing

# Автотесты

python -m unittest discover -s tests -v
```

При обычном запуске эмулятор выводит состояние после каждой команды до `HALT`. В режиме `--step` Enter выполняет одну команду, `q` завершает сеанс. Параметр `--limit` задаёт максимальное число команд (по умолчанию 10 000). В качестве входа можно указать свой UTF-8-файл с ассемблерным текстом.

Спецификация, разбор требований и контрольные листинги приведены в [отчёте](docs/report.md).
