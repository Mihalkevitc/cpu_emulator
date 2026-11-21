    MOV SI, A
    MOV DI, B
    MOV CX, [SI]
    ADD SI, 2
    ADD DI, 2
    MOV R8, 0
    MOV R9, 0
    MOV R10, 0

DOT_LOOP:
    MOV AX, [SI]
    MOV BX, [DI]
    MUL BX

    ; Перенос проходит через все три слова результата.
    ADD R8, AX
    ADC R9, DX
    ADC R10, 0

    ADD SI, 2
    ADD DI, 2
    DEC CX
    JNE DOT_LOOP

    MOV [RESULT], R8
    MOV [RESULT+2], R9
    MOV [RESULT+4], R10
    HALT

A: DW 6, 65535, 65535, 65535, 65535, 65535, 65535
B: DW 6, 65535, 65535, 65535, 65535, 65535, 65535
RESULT: DW 0, 0, 0
