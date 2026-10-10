import sys
from typing import List, Optional, Tuple
from utils import CPUMode
from instruction import Instruction
from memory import MemoryManager, MemoryAccessError

class CPU:
    PC_ADDR = 0
    SP_ADDR = 1
    SYSCALL_RESULT_ADDR = 2
    INST_COUNT_ADDR = 3
    SYSCALL_SAVE_PC_ADDR = 4

    def __init__(self, memory_size: int = 20000, debug_mode: int = 0):
        self.memory_manager = MemoryManager(memory_size)
        self.instructions: List[Optional[Instruction]] = []
        self.halted = False
        self.mode = CPUMode.KERNEL
        self.debug_mode = debug_mode
                
        # Initialize special registers
        self._initialize_registers()

    def _initialize_registers(self):
        """Initialize CPU registers to default values"""
        # Stack pointer starts at top of memory (stack grows downward)
        self.memory_manager.set_value_unchecked(self.SP_ADDR, self.memory_manager.size - 1)
        self.memory_manager.set_value_unchecked(self.PC_ADDR, 0)
        self.memory_manager.set_value_unchecked(self.INST_COUNT_ADDR, 0)
        self.memory_manager.set_value_unchecked(self.SYSCALL_RESULT_ADDR, 0)

    def load_program_data(self, initial_data: List[Tuple[int, int]], instructions: List[Optional[Instruction]]):
        """Load program data and instructions into CPU memory"""
        # Reset CPU state
        self.memory_manager = MemoryManager(self.memory_manager.size)
        self._initialize_registers()
        self.halted = False
        self.mode = CPUMode.KERNEL

        # Load initial data
        for addr, value in initial_data:
            self.memory_manager.set_value_unchecked(addr, value)
        
        self.instructions = instructions

        # Validate initial PC
        initial_pc = self.get_pc()

        if not self.instructions:
            print("Warning: No instructions loaded. CPU will likely halt immediately.")
        elif not (0 <= initial_pc < len(self.instructions)):
            print(f"Warning: Initial PC {initial_pc} is out of bounds. Resetting to 0.")
            self.set_pc(0)
        elif self.instructions[initial_pc] is None:
            print(f"Warning: Initial PC {initial_pc} points to None instruction.")

    def get_pc(self) -> int:
        return self.memory_manager.get_value_unchecked(self.PC_ADDR)

    def set_pc(self, value: int):
        self.memory_manager.set_value_unchecked(self.PC_ADDR, value)

    def get_sp(self) -> int:
        return self.memory_manager.get_value_unchecked(self.SP_ADDR)

    def set_sp(self, value: int):
        self.memory_manager.set_value_unchecked(self.SP_ADDR, value)

    def _push_to_stack(self, value: int):
        """Push value onto stack"""
        sp = self.get_sp() - 1
        if sp < 0:
            raise MemoryAccessError("Stack overflow: SP less than 0", sp, self.mode)
        self.set_sp(sp)
        self.memory_manager.write(sp, value, self.mode)

    def _pop_from_stack(self) -> int:
        """Pop value from stack"""
        sp = self.get_sp()
        if sp >= self.memory_manager.size:
            raise MemoryAccessError("Stack underflow: SP at or above memory size", sp, self.mode)
        value = self.memory_manager.read(sp, self.mode)
        self.set_sp(sp + 1)
        return value

    def _execute_single_instruction(self, inst: Instruction) -> bool:
        """Execute a single instruction. Returns True if PC should auto-increment."""
        opcode = inst.opcode
        operands = inst.operands
        increment_pc_after = True

        if opcode == "SET":  # SET B A      
            if len(operands) != 2:
                raise ValueError(f"SET requires 2 operands, got {len(operands)}")
            value, addr = operands[0], operands[1]
            self.memory_manager.write(addr, value, self.mode)

            if addr == self.PC_ADDR:
                increment_pc_after = False # Don't auto-increment
        
        elif opcode == "CPY":  # CPY A1 A2
            if len(operands) != 2:
                raise ValueError(f"CPY requires 2 operands")
            src_addr, dest_addr = operands[0], operands[1]
            val = self.memory_manager.read(src_addr, self.mode)
            self.memory_manager.write(dest_addr, val, self.mode)

        elif opcode == "CPYI":  # CPYI A1 A2
            if len(operands) != 2:
                raise ValueError(f"CPYI requires 2 operands")
            ptr_addr, dest_addr = operands[0], operands[1]
            actual_src_addr = self.memory_manager.read(ptr_addr, self.mode)
            val = self.memory_manager.read(actual_src_addr, self.mode)
            self.memory_manager.write(dest_addr, val, self.mode)

        elif opcode == "CPYI2":  # CPYI2 A1 A2
            if len(operands) != 2:
                raise ValueError(f"CPYI2 requires 2 operands")
            src_ptr_addr, dest_ptr_addr = operands[0], operands[1]
            actual_src_addr = self.memory_manager.read(src_ptr_addr, self.mode)
            val_to_copy = self.memory_manager.read(actual_src_addr, self.mode)
            actual_dest_addr = self.memory_manager.read(dest_ptr_addr, self.mode)
            self.memory_manager.write(actual_dest_addr, val_to_copy, self.mode)
        
        elif opcode == "ADD":  # ADD A B
            if len(operands) != 2:
                raise ValueError(f"ADD requires 2 operands")
            addr, value_to_add = operands[0], operands[1]
            current_val = self.memory_manager.read(addr, self.mode)
            self.memory_manager.write(addr, current_val + value_to_add, self.mode)

        elif opcode == "ADDI":  # ADDI A1 A2 -> M[A2] = M[A1] + M[A2]
            if len(operands) != 2:
                raise ValueError(f"ADDI requires 2 operands")
            src_addr, dest_addr = operands[0], operands[1]
            val_to_add = self.memory_manager.read(src_addr, self.mode)
            current_val = self.memory_manager.read(dest_addr, self.mode)
            self.memory_manager.write(dest_addr, current_val + val_to_add, self.mode)

        elif opcode == "SUBI":  # SUBI A1 A2 -> M[A2] = M[A1] - M[A2]
            if len(operands) != 2:
                raise ValueError(f"SUBI requires 2 operands")
            addr_a1, addr_a2 = operands[0], operands[1]
            val_a1 = self.memory_manager.read(addr_a1, self.mode)
            val_a2 = self.memory_manager.read(addr_a2, self.mode)
            self.memory_manager.write(addr_a2, val_a1 - val_a2, self.mode)

        elif opcode == "JIF":  # JIF A C
            if len(operands) != 2:
                raise ValueError(f"JIF requires 2 operands")
            addr_a, target_pc = operands[0], operands[1]
            if self.memory_manager.read(addr_a, self.mode) <= 0:
                self.set_pc(target_pc)
                increment_pc_after = False
        
        elif opcode == "PUSH":  # PUSH A
            if len(operands) != 1:
                raise ValueError(f"PUSH requires 1 operand")
            addr_a = operands[0]
            val = self.memory_manager.read(addr_a, self.mode)
            self._push_to_stack(val)

        elif opcode == "POP":  # POP A
            if len(operands) != 1:
                raise ValueError(f"POP requires 1 operand")
            addr_a = operands[0]
            val = self._pop_from_stack()
            self.memory_manager.write(addr_a, val, self.mode)
        
        elif opcode == "CALL":  # CALL C
            if len(operands) != 1:
                raise ValueError(f"CALL requires 1 operand")
            target_pc = operands[0]
            self._push_to_stack(self.get_pc() + 1)
            self.set_pc(target_pc)
            increment_pc_after = False
        
        elif opcode == "RET":  # RET
            if len(operands) != 0:
                raise ValueError(f"RET requires 0 operands")
            return_addr = self._pop_from_stack()
            self.set_pc(return_addr)
            increment_pc_after = False
        
        elif opcode == "HLT":  # HLT - CPU halt
            self.halted = True
            increment_pc_after = False

        elif opcode == "USER":  # USER A
            if len(operands) != 1:
                raise ValueError(f"USER requires 1 operand")
            addr_containing_user_pc = operands[0]
            user_pc_start = self.memory_manager.read(addr_containing_user_pc, self.mode)
            self.mode = CPUMode.USER
            self.set_pc(user_pc_start)
            if self.debug_mode > 0:
                print(f"CPU: Switched to USER mode. Jumping to PC={user_pc_start}")
            increment_pc_after = False

            if self.debug_mode == 3:
                self.print_thread_table_to_stderr()
        elif opcode == "SYSCALL":
            # Auto-switch to KERNEL mode for syscalls
            if self.mode == CPUMode.USER and self.debug_mode > 0:
                print(f"CPU: SYSCALL from USER mode, switching to KERNEL mode.")
            self.mode = CPUMode.KERNEL
            

            thread_return_pc = self.get_pc() + 1
            self.memory_manager.set_value_unchecked(CPU.SYSCALL_SAVE_PC_ADDR, thread_return_pc)
            syscall_type = str(operands[0]).upper()
            
            increment_pc_after = False
            if syscall_type == "PRN":
                # PRN is handled in Python as per requirements
                if len(operands) != 2:
                    raise ValueError(f"SYSCALL PRN requires 1 address operand")
                address_of_pointer = operands[1]
                actual_address_to_print = self.memory_manager.read(address_of_pointer, self.mode)
                val_to_print = self.memory_manager.read(actual_address_to_print, self.mode)
                print(f"{val_to_print}")  # Output as specified
            
                # Jump to PRN handler in OS
                self.set_pc(600)  # PRN handler address in your OS
                
            elif syscall_type == "HLT":  
                # HLT is handled by OS code - jump to OS handler
                if self.debug_mode > 0:
                    print(f"SYSCALL.HLT: Jumping to OS HLT handler.")
                self.set_pc(550)  # HLT handler address in your OS
            
            elif syscall_type == "YIELD":
                # YIELD is handled by OS code - jump to OS handler  
                if self.debug_mode > 0:
                    print(f"SYSCALL.YIELD: Jumping to OS YIELD handler.")
                self.set_pc(500)  # YIELD handler address in your OS                
            else:
                raise ValueError(f"Unknown SYSCALL type '{syscall_type}'")

            if self.debug_mode == 3:
                self.print_thread_table_to_stderr()
        
        else:
            raise ValueError(f"Unknown opcode '{opcode}'")
        
        return increment_pc_after

    def step(self) -> bool:
        """Execute one instruction cycle. Returns True if CPU can continue."""
        if self.halted:
            return False
        
        pc = self.get_pc()
        
        # Validate PC
        if not (0 <= pc < len(self.instructions)):
            print(f"Error: PC ({pc}) out of bounds. Halting.", file=sys.stderr)
            self.halted = True
            return False
        
        current_instruction = self.instructions[pc]
        if current_instruction is None:
            print(f"Error: PC ({pc}) points to None instruction. Halting.", file=sys.stderr)
            self.halted = True
            return False

        if self.debug_mode == 1 or self.debug_mode == 2:
            print(f"CPU Pre-Exec: PC={pc:03d} SP={self.get_sp():04d} MODE={self.mode.name} "
                f"IC={self.memory_manager.get_value_unchecked(self.INST_COUNT_ADDR):<4} | "
                f"Exec: {current_instruction}")

        try:
            should_increment_pc = self._execute_single_instruction(current_instruction)
            
            if not self.halted:
                if should_increment_pc:
                    self.set_pc(pc + 1)
                # Increment instruction counter
                current_instr_count = self.memory_manager.get_value_unchecked(self.INST_COUNT_ADDR)
                self.memory_manager.set_value_unchecked(self.INST_COUNT_ADDR, current_instr_count + 1)

        except MemoryAccessError as e:
            print(f"FATAL Error at PC {pc}: {e}. Halting.", file=sys.stderr)
            self.halted = True
            return False
        except ValueError as e:
            print(f"FATAL Error at PC {pc}: {e}. Halting.", file=sys.stderr)
            self.halted = True
            return False
        except Exception as e:
            import traceback
            print(f"UNEXPECTED FATAL Error at PC {pc}: {e}. Halting.", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            self.halted = True
            return False

        if self.halted:
            if self.debug_mode >= 1:
                print("CPU Halted.")
            return False

        # Debug output
        if self.debug_mode == 1 or (self.debug_mode == 2 and not self.halted):
            self.print_memory_state_to_stderr()
        if self.debug_mode == 2 and not self.halted:
            input("  Press Enter for next tick...")
        
        return True

    def is_halted(self) -> bool:
        return self.halted

    def print_memory_state_to_stderr(self):
        """Print current memory state to stderr"""
        print("--- Memory Dump ---", file=sys.stderr)
        print(f"  PC: {self.get_pc():03d} SP: {self.get_sp():04d} Mode: {self.mode.name} "
              f"TotalInst: {self.memory_manager.get_value_unchecked(self.INST_COUNT_ADDR)}", file=sys.stderr)
        print(f"  SyscallResult: {self.memory_manager.get_value_unchecked(self.SYSCALL_RESULT_ADDR)}", file=sys.stderr)
        
        non_zero_mem = self.memory_manager.get_all_non_zero()
        if not non_zero_mem:
            print("  (All memory is zero)", file=sys.stderr)
        else:
            print_count = 0
            limit = 20
            for addr, val in sorted(non_zero_mem.items()):
                if 0 <= addr <= self.INST_COUNT_ADDR:
                    print(f"  MEM[{addr:04d}]: {val:<5} (Register)", file=sys.stderr)
                    print_count += 1
                elif self.get_sp() - 5 <= addr <= self.get_sp() + 5:
                    is_sp_val = "(SP)" if addr == self.get_sp() else ""
                    print(f"  MEM[{addr:04d}]: {val:<5} {is_sp_val}", file=sys.stderr)
                    print_count += 1
                elif print_count < limit:
                    print(f"  MEM[{addr:04d}]: {val:<5}", file=sys.stderr)
                    print_count += 1
            if len(non_zero_mem) > print_count:
                print(f"  ... and {len(non_zero_mem) - print_count} other non-zero locations.", file=sys.stderr)
        print("--- End Memory Dump ---\n", file=sys.stderr)

    def print_final_memory_dump(self):
        """Print final memory state"""
        print("\n--- Final Memory State ---", file=sys.stderr)
        print(f"PC: {self.get_pc()} SP: {self.get_sp()} Mode: {self.mode.name} "
              f"TotalInst: {self.memory_manager.get_value_unchecked(self.INST_COUNT_ADDR)}", file=sys.stderr)
        non_zero_mem = self.memory_manager.get_all_non_zero()
        if not non_zero_mem:
            print("(All memory is zero)", file=sys.stderr)
        else:
            for addr, val in sorted(non_zero_mem.items()):
                print(f"  MEM[{addr:05d}]: {val}", file=sys.stderr)
        print("--- End Final Memory State ---", file=sys.stderr)

    def print_thread_table_to_stderr(self):
        """Print actual thread table from OS memory"""
        print("--- Thread Table Dump ---", file=sys.stderr)
        
        # Thread table layout:
        # Base address: 100
        # Each thread takes 80 memory locations
        # Thread N base address = 100 + N * 80
        
        THREAD_TABLE_BASE = 100
        THREAD_SIZE = 80
        MAX_THREADS = 11
        
        # Offsets within each thread block
        THREAD_ID_OFFSET = 0
        STATE_OFFSET = 1
        PC_OFFSET = 2
        SP_OFFSET = 3
        FIRST_EXEC_TIME_OFFSET = 4
        LAST_START_TIME_OFFSET = 5
        TOTAL_EXEC_INST_OFFSET = 6
        LAST_IC_OFFSET = 7
        BLOCK_DURATION_OFFSET = 8
        
        # State mappings
        STATE_NAMES = {
            1: "READY",
            2: "RUNNING", 
            3: "BLOCKED",
            4: "HALTED"
        }
        
        for thread_id in range(MAX_THREADS):
            thread_base_addr = THREAD_TABLE_BASE + thread_id * THREAD_SIZE
            
            # Read thread properties
            stored_thread_id = self.memory_manager.get_value_unchecked(thread_base_addr + THREAD_ID_OFFSET)
            state = self.memory_manager.get_value_unchecked(thread_base_addr + STATE_OFFSET)
            pc = self.memory_manager.get_value_unchecked(thread_base_addr + PC_OFFSET)
            sp = self.memory_manager.get_value_unchecked(thread_base_addr + SP_OFFSET)
            first_exec_time = self.memory_manager.get_value_unchecked(thread_base_addr + FIRST_EXEC_TIME_OFFSET)
            last_start_time = self.memory_manager.get_value_unchecked(thread_base_addr + LAST_START_TIME_OFFSET)
            total_exec_inst = self.memory_manager.get_value_unchecked(thread_base_addr + TOTAL_EXEC_INST_OFFSET)
            last_ic = self.memory_manager.get_value_unchecked(thread_base_addr + LAST_IC_OFFSET)
            block_duration = self.memory_manager.get_value_unchecked(thread_base_addr + BLOCK_DURATION_OFFSET)
            
            # Convert state number to name
            state_name = STATE_NAMES.get(state, f"UNKNOWN({state})")
            
            # Determine thread type
            thread_type = "OS" if thread_id == 0 else f"T{thread_id}"
            
            # Only print threads that have been initialized (non-zero thread ID or state)
            if stored_thread_id != 0 or state != 0 or pc != 0:
                print(f"  {thread_type:3}: ID={stored_thread_id:2} State={state_name:7} PC={pc:4} SP={sp:5} "
                    f"FirstExec={first_exec_time:4} LastStart={last_start_time:4} "
                    f"TotalInst={total_exec_inst:4} LastIC={last_ic:4} BlockDur={block_duration:3}", 
                    file=sys.stderr)
            else:
                # For uninitialized threads, just show basic info
                print(f"  {thread_type:3}: UNINITIALIZED", file=sys.stderr)
        
        print("--- End Thread Table Dump ---", file=sys.stderr)