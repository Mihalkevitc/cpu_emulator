    MOV SI, A
    MOV CX, [SI]
    ADD SI, 2
    MOV AX, [SI]
    DEC CX
    JE SAVE

SCAN:
    ADD SI, 2
    MOV BX, [SI]
    CMP AX, BX
    JAE NEXT
    MOV AX, BX
NEXT:
    DEC CX
    JNE SCAN

SAVE:
    MOV [MAX_RESULT], AX
    HALT

; Длина массива положительна и записана перед элементами.
A: DW 6, 12, 65535, 7, 1024, 3, 90
MAX_RESULT: DW 0
