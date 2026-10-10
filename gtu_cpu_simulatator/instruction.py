# gtu_cpu_simulator/instruction.py
from typing import List, Union

class Instruction:
    """Represents a single CPU instruction"""
    def __init__(self, opcode: str, operands: List[Union[int, str]], line_num: int = 0, original_line: str = ""):
        self.opcode = opcode.upper()  # Standardize opcode case
        self.operands = operands
        self.line_num = line_num  # Line number from the source file
        self.original_line = original_line  # For debugging

    def __repr__(self):
        # Use original_line if available and not too long, otherwise format
        if self.original_line:
            return f"L{self.line_num}: {self.original_line.strip()}"
        return f"L{self.line_num}: {self.opcode} {' '.join(map(str, self.operands))}"