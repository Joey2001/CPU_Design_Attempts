'''
This is a translator tool for my custom 16-bit CPU.
I created a hybrid opcode that distinguishes the instruction type
as well as the ALU function when nessesary. Most instructions follow
the rule with the exception of the JAL, JALR, and SB instructions.
I wanted to avoid encoding 00000 as an opcode, and was able to keep
the core functionality that I wanted.

BIT FIELD
R-type: | f2  | rs2 | rs1 |  rd | OP/Func
I-type: | imm       | rs1 |  rd | OP/Func
S-type: | imm | rs2 | rs1 | imm | OP/Func
B-type: | imm | rs2 | rs1 | imm | OP/Func
U-type: |       imm       |  rd | OP/Func
J-type: |       imm       |  rd | OP/Func
'''

import re

REG_SIZE = 3
BSI_IMM_SIZE = 5
MAX_INST_PER_LINE = 8

INSTRUCTION_SET = {
#     Register
    'ADD'   : ('10000', 'R'),
    'SUB'   : ('10000', 'R'),
    'XOR'   : ('10100', 'R'),
    'OR'    : ('10110', 'R'),
    'AND'   : ('10111', 'R'),
    'SLL'   : ('10001', 'R'),
    'SRL'   : ('10101', 'R'),
    'SRA'   : ('10101', 'R'),
    'SLT'   : ('10010', 'R'),
    'SLTU'  : ('10011', 'R'),
#     Immediate
    'ADDI'  : ('11000', 'I'),
    'XORI'  : ('11100', 'I'),
    'ORI'   : ('11110', 'I'),
    'ANDI'  : ('11111', 'I'),
    'SLLI'  : ('11001', 'I'),
    'SRLI'  : ('11101', 'I'),
    'SRAI'  : ('11101', 'I'),
    'SLTI'  : ('11010', 'I'),
    'SLTIU' : ('11011', 'I'),
#     Memory
    'LB'    : ('00100', 'I'),
    'LH'    : ('00101', 'I'),
    'LBU'   : ('00110', 'I'),
    'SH'    : ('00111', 'S'),
    'SB'    : ('00001', 'S'),
#     Branch
    'BEQ'   : ('01000', 'B'),
    'BNE'   : ('01001', 'B'),
    'BLT'   : ('01100', 'B'),
    'BGE'   : ('01101', 'B'),
    'BLTU'  : ('01110', 'B'),
    'BGEU'  : ('01111', 'B'),
#     Jump
    'JAL'   : ('01011', 'J'),
    'JALR'  : ('01010', 'I'),
#     Upper load
    'LUI'   : ('00010', 'U'),
    'AUIPC' : ('00011', 'U')
}

# Only works with decimal numbers, I wanted a general function
# to convert register numbers, offsets, and immediates
def enc_num(reg_or_imm):
    filtered = re.sub('[^0-9]','', reg_or_imm)
    num_val = int(filtered) % 512

    return format(num_val, '08b')

# Converts assembly code into hex for a dump file
def enc_instr(instruction):
    instruction = instruction.upper()       # makes sure casing matches
    parts = instruction.split()
    find_op = parts[0]   # determines what happens when selecting rs1, rs2, rd, immediate & offsets

    # instruction will always be here, unless it's not valid
    try:
        opcode, inst_type = INSTRUCTION_SET[find_op]
    except KeyError:
        raise ValueError(f"Unhandled instruction format: {instruction}")
    
    # checks if it's a memory op or a jump and link reg
    if(find_op in ["LB", "LH", "LBU", "SH", "SB", "JALR"]):
        rd = enc_num(parts[1])[-REG_SIZE:]

        if(inst_type == "S"):
            rs2 = rd

        # immediate is the offset
        get_imm = parts[2].split("(", 1)
        imm = enc_num(get_imm[0])[-BSI_IMM_SIZE:]

        # register num is after the first "("
        rs1 = enc_num(get_imm[1])[-REG_SIZE:]
    elif(inst_type == "B"):
        rs1 = enc_num(parts[1])[-REG_SIZE:]
        rs2 = enc_num(parts[2])[-REG_SIZE:]

        imm = enc_num(parts[3])[-BSI_IMM_SIZE:]

    elif(inst_type == "U"):
        rd = enc_num(parts[1])[-REG_SIZE:]

        imm = enc_num(parts[2])

    elif(inst_type == "R"):
        rd = enc_num(parts[1])[-REG_SIZE:]
        rs1 = enc_num(parts[2])[-REG_SIZE:]
        rs2 = enc_num(parts[3])[-REG_SIZE:]
    elif(inst_type == "I"):
        rd = enc_num(parts[1])[-REG_SIZE:]
        rs1 = enc_num(parts[2])[-REG_SIZE:]

        imm = enc_num(parts[3])[-BSI_IMM_SIZE:]

        if(find_op == "SRAI"):
            imm = "1" + imm[1:]
        elif (find_op in ["SLLI", "SRLI"]):
            imm = "0" + imm[1:]
    
    if(inst_type == "R"):
        f2 = "00"
        # op alt only active on SUB and SRA
        if find_op in ["SUB", "SRA"]:
            f2 = "10"
        binary = f"{f2}{rs2}{rs1}{rd}{opcode}"
    elif(inst_type == "I"):
        binary = f"{imm}{rs1}{rd}{opcode}"
    elif(inst_type in ["S", "B"]):
        binary = f"{imm[:2]}{rs2}{rs1}{imm[2:]}{opcode}"
    elif(inst_type == "U"):
        binary = f"{imm}{rd}{opcode}"
    elif(inst_type == "J"):
        rd = enc_num(parts[1])[-REG_SIZE:]
        imm = enc_num(parts[2])

        binary = f"{imm}{rd}{opcode}"
    else:
        binary = "NOT VALID"

    return binary

def translate_file(input_file, output_file):
    instruction_on_line = 0
    try:
        open(output_file, 'w').close()

        with open(input_file, 'r') as in_file, open(output_file, 'w') as out_file:
            out_file.write("v2.0 raw\n")
            for line in in_file:
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                try:
                    binary = enc_instr(line)
                    bin_int = int(binary, 2)
                    bin_hex = hex(bin_int)[2:].zfill(4)

                    out_file.write(f"{bin_hex}")
                    instruction_on_line += 1
                    if(instruction_on_line == 8):
                        out_write = "\n"
                        instruction_on_line = 0
                    else:
                        out_write = " "
                    out_file.write(out_write)
                except ValueError as e:
                    print(f"Error processing line: {line} - {e}")

        print(f"Hexadecimal values written to {output_file}")
    except FileNotFoundError:
        print(f"File {input_file} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

translate_file('input.txt', 'output.txt')