# gtu_cpu_simulator/loader.py
from typing import List, Tuple, Dict, Optional
from instruction import Instruction

# Define a custom exception class that inherits from Python's built-in ValueError.
class InstructionParseError(ValueError):
    pass

# The ProgramLoader class is responsible for reading a .gtu312 file,
class ProgramLoader:

    # Constructor: Initializes the ProgramLoader with the filename of the program to load.
    def __init__(self, filename: str):
        self.filename = filename

    # Helper method to parse operands for an instruction.
    def _parse_operands(self, opcode: str, operand_parts: List[str], line_num: int) -> List:
        """Helper to parse operands, handling SYSCALL specifically."""
        operands = []

        # SYSCALL instructions have a special operand format:
        # The first operand is a string (syscall type), subsequent ones might be ints or non-existent.
        if opcode == "SYSCALL":
            # SYSCALL must have at least one operand (the type).
            if not operand_parts:
                raise InstructionParseError(f"L{line_num}: SYSCALL requires a type.")
            
            # The first operand part is the syscall type (e.g., "PRN", "HLT"). Convert to uppercase.
            syscall_type_str = operand_parts[0].upper()

            # Add the syscall type string as the first parsed operand.
            operands.append(syscall_type_str)

            # Handle specific SYSCALL types: 
            if syscall_type_str == "PRN":

                # SYSCALL PRN expects an address as a second operand.
                if len(operand_parts) < 2:
                    raise InstructionParseError(f"L{line_num}: SYSCALL PRN requires an address.")
                try:
                    # Attempt to convert the second operand part to an integer.
                    operands.append(int(operand_parts[1]))
                except ValueError:
                    raise InstructionParseError(f"L{line_num}: SYSCALL PRN address must be an integer.")

            # These syscalls take no additional arguments.
            elif syscall_type_str in ["HLT", "YIELD"]:
                # If extra arguments are provided, print a warning
                if len(operand_parts) > 1:
                    print(f"Warning L{line_num}: SYSCALL {syscall_type_str} takes no arguments, extras ignored.")
            else:
                raise InstructionParseError(f"L{line_num}: Unknown SYSCALL type: {syscall_type_str}")
        else:
            # For all other opcodes, assume operands are integers. 
            try:
                # Use a list comprehension to try and convert all operand parts to integers.
                operands = [int(x) for x in operand_parts]
            except ValueError:
                raise InstructionParseError(f"L{line_num}: Non-integer operand for {opcode}: {operand_parts}")
        return operands


    # Main method to load and parse the program file.
    # Returns a tuple containing:
    #  1. A list of (address, value) tuples for initial memory data.
    #  2. A list of Instruction objects (or None for unused instruction numbers).
    def load(self) -> Tuple[List[Tuple[int, int]], List[Optional[Instruction]]]:
        # List to store (address, value) pairs from the "DATA SECTION".
        initial_memory_data: List[Tuple[int, int]] = []
        # Dictionary to store parsed instructions. Key is instruction number, value is Instruction object.
        raw_instructions: Dict[int, Instruction] = {} 
        # Keep track of the highest instruction number encountered to size the final list.
        max_inst_num = -1

        try:
            with open(self.filename, 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            raise 

        # Flags to track whether the parser is currently inside a DATA or INSTRUCTION section.
        in_data_section = False
        in_instruction_section = False


        # Iterate over each line read from the file, with its index.
        for line_idx, line_content in enumerate(lines):
            line_num_for_error = line_idx + 1
            original_line_text = line_content.strip()

            # Pre-process the line:
            # 1. Split the line at the first '#' character to remove comments. Take the part before it.
            # 2. Strip leading/trailing whitespace from the (potentially comment-removed) line.
            line = line_content.split('#')[0].strip()
            
            # If the line is empty after removing comments and whitespace, skip it.
            if not line:
                continue

            # Check if the line is a section delimiter (case-insensitive).
            if line.upper() == "BEGIN DATA SECTION":
                in_data_section = True
                in_instruction_section = False
                continue
            elif line.upper() == "END DATA SECTION":
                in_data_section = False
                continue
            elif line.upper() == "BEGIN INSTRUCTION SECTION":
                in_instruction_section = True
                in_data_section = False
                continue
            elif line.upper() == "END INSTRUCTION SECTION":
                in_instruction_section = False
                continue

            # If the line is not a section marker and not empty, try to parse it.
            # Split the line into parts based on whitespace.
            parts = line.split()

            # This check is somewhat redundant if 'if not line:' above caught empty lines,
            if not parts: 
                continue

            if in_data_section:
                if len(parts) >= 2:
                    try:
                        # Attempt to convert the first part to an integer (address)
                        # and the second part to an integer (value).
                        addr, value = int(parts[0]), int(parts[1])
                        initial_memory_data.append((addr, value))
                    except ValueError:
                        print(f"Warning L{line_num_for_error}: Invalid data format: '{original_line_text}'. Expected <addr> <value>.")
                else:
                    print(f"Warning L{line_num_for_error}: Invalid data line: '{original_line_text}'. Expected <addr> <value>.")
            
            elif in_instruction_section:
                if len(parts) >= 2: 
                    try:
                        # First part is instruction number.
                        inst_num_from_file = int(parts[0])
                        # Second part is the opcode, and the rest are operands.
                        opcode = parts[1].upper()
                        # Validate the opcode is a valid instruction.
                        # The rest of the parts are potential operands. Pass them to the helper.
                        operands = self._parse_operands(opcode, parts[2:], line_num_for_error)
                        

                        # Check for duplicate instruction numbers.
                        if inst_num_from_file in raw_instructions:
                            print(f"Warning L{line_num_for_error}: Duplicate instruction number {inst_num_from_file}. Overwriting previous: {raw_instructions[inst_num_from_file]}")
                        
                        # Create an Instruction object.
                        raw_instructions[inst_num_from_file] = Instruction(opcode, operands, inst_num_from_file, original_line_text)
                        
                        # Update the maximum instruction number encountered.
                        max_inst_num = max(max_inst_num, inst_num_from_file)
                    except ValueError as e: 
                        print(f"Warning L{line_num_for_error}: Invalid instruction format: '{original_line_text}' - {e}")
                    except InstructionParseError as e:
                        print(f"Warning: {e}")
                else:
                    print(f"Warning L{line_num_for_error}: Invalid instruction line (too short): '{original_line_text}'.")
        

        # After processing all lines, convert the dictionary of raw_instructions
        # into a list of instructions, padded with None for any missing instruction numbers.
        final_instructions: List[Optional[Instruction]] = []


        if max_inst_num != -1:

            # Create a list of size (max_inst_num + 1), initialized with Nones.
            # This ensures instructions can be accessed by their number as an index.
            final_instructions = [None] * (max_inst_num + 1)

            # Iterate through the parsed instructions.
            for i, inst in raw_instructions.items():
                # Check if the instruction number is within valid bounds.
                if 0 <= i < len(final_instructions):
                    final_instructions[i] = inst
                else:
                    print(f"Warning: Instruction number {i} is out of expected range after parsing.")
        

        if not final_instructions and max_inst_num == -1 and in_instruction_section:
            print("Warning: Instruction section declared but no valid instructions found.")

        return initial_memory_data, final_instructions