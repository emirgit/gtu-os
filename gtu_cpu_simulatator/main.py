# main.py
import sys
import argparse
import os
from gtu_cpu import CPU
from loader import ProgramLoader, InstructionParseError
from memory import MemoryAccessError


class Simulator:
    """Main simulator class that orchestrates the CPU simulation"""
    DEFAULT_MAX_CYCLES = 500000

    def __init__(self, program_filename: str, debug_mode: int, memory_size: int = 20000, max_cycles: int = DEFAULT_MAX_CYCLES):
        # Stores the program filename and initializes the CPU
        self.program_filename = program_filename
        # Set debug mode (0-3)
        self.debug_mode = debug_mode
        # Validate memory size
        self.cpu = CPU(memory_size=memory_size, debug_mode=self.debug_mode)
        # Validate maximum cycles
        self.max_cycles = max_cycles
        print(f"Simulator initialized for '{program_filename}'.")
        print(f"Debug: {debug_mode}, MemSize: {memory_size}, MaxCycles: {max_cycles}")

    def run(self):
        """Main simulation loop"""
        # Load program
        try:
            print(f"Loading program: {self.program_filename}...")
            # Call the loader's load() method, which reads the file,
            # parses data and instructions.
            loader = ProgramLoader(self.program_filename)
            initial_data, instructions = loader.load()
            
            if not instructions:
                print("Warning: No instructions found in program file.")
                return
            
            # Load initial data into CPU memory
            self.cpu.load_program_data(initial_data, instructions)
            print("Program loaded into CPU successfully.")
            
            # Print initial state for debug modes
            if self.debug_mode > 0:
                print(f"Initial PC: {self.cpu.get_pc()}")
                print(f"Initial SP: {self.cpu.get_sp()}")
                print(f"Total instructions loaded: {len(instructions)}")

        # Error handling for the loading phase
        except FileNotFoundError:
            print(f"Error: Program file '{self.program_filename}' not found.", file=sys.stderr)
            sys.exit(1)
        except InstructionParseError as e:
            print(f"Error parsing program file: {e}", file=sys.stderr)
            sys.exit(1)
        except MemoryAccessError as e:
            print(f"Memory Error during program loading: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            import traceback
            print(f"Unexpected error during program loading: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)

        # Run simulation
        print(f"\nStarting CPU simulation (Debug Level: {self.debug_mode})...")
        if self.debug_mode == 2:
            print("Debug Mode 2: Press Enter after each instruction to continue.")
        
        # Counter for simulated CPU cycles
        executed_cycles = 0
        
        try:
            # The main simulation loop: continues as long as the CPU is not halted
            while not self.cpu.is_halted():
                # step() returns False if CPU halted or a fatal error occurred during the step
                if not self.cpu.step():
                    break
                
                executed_cycles += 1
                
                # Safety break for runaway programs
                if executed_cycles >= self.max_cycles:
                    print(f"\nWarning: Simulation exceeded maximum cycle count ({self.max_cycles}). Forcibly halting.", file=sys.stderr)
                    self.cpu.halted = True
                    break
                    
        except KeyboardInterrupt:
            print("\nSimulation interrupted by user (Ctrl+C). Halting.", file=sys.stderr)
            self.cpu.halted = True

        if self.debug_mode == 3:
            self.cpu.print_thread_table_to_stderr()

        # Print final results
        print(f"\n{'='*50}")
        print(f"CPU Simulation Finished")
        print(f"{'='*50}")
        print(f"Status: {'HALTED' if self.cpu.is_halted() else 'RUNNING (unexpected)'}")
        print(f"Total CPU cycles simulated: {executed_cycles}")
        final_instr_count = self.cpu.memory_manager.get_value_unchecked(CPU.INST_COUNT_ADDR)
        print(f"Total instructions executed: {final_instr_count}")
        print(f"Final PC: {self.cpu.get_pc()}")
        print(f"Final SP: {self.cpu.get_sp()}")
        print(f"CPU Mode: {self.cpu.mode.name}")
        
        # Print final memory dump for debug mode 0 or if simulation was interrupted
        if self.debug_mode == 0 or executed_cycles >= self.max_cycles:
            self.cpu.print_final_memory_dump()


def find_program_file(filename: str) -> str:
    """Try to find the program file in various locations"""
    # If absolute path or exists in current directory
    if os.path.isabs(filename) or os.path.exists(filename):
        return filename
    
    # Try in 'programs' subdirectory relative to script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    potential_paths = [
        os.path.join(script_dir, "programs", filename),
        os.path.join(os.getcwd(), "programs", filename),
        os.path.join(script_dir, filename),
    ]
    
    for path in potential_paths:
        if os.path.exists(path):
            return path
    
    # If not found, return original filename (will cause FileNotFoundError later)
    return filename


def main():
    """Main entry point with command line argument parsing"""
    parser = argparse.ArgumentParser(
        description="GTU-C312 CPU Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Debug Modes:
  0: Run program and show final memory dump
  1: Show memory dump after each instruction
  2: Step-by-step execution (press Enter to continue)
  3: Show thread table on context switches/syscalls

Example usage:
  python main.py program.gtu312 -D 0
  python main.py test_program.gtu312 -D 1 --memsize 10000
        """
    )
    
    # --- Define Command-Line Arguments ---
    parser.add_argument("filename", 
                       help="Path to the GTU-C312 program file")
    parser.add_argument("-D", "--debug", 
                       type=int, 
                       choices=[0, 1, 2, 3], 
                       default=0,
                       help="Debug level (0-3)")
    parser.add_argument("--memsize", 
                       type=int, 
                       default=20000,
                       help="Total CPU memory size (default: 20000)")
    parser.add_argument("--maxcycles", 
                       type=int, 
                       default=Simulator.DEFAULT_MAX_CYCLES,
                       help=f"Maximum simulation cycles before auto-halt (default: {Simulator.DEFAULT_MAX_CYCLES})")
    parser.add_argument("--verbose", 
                       action="store_true",
                       help="Enable verbose output")
    
    args = parser.parse_args()

    # Validate arguments
    if args.memsize < 1000:
        print("Error: Memory size must be at least 1000 (for user space starting at 1000)", file=sys.stderr)
        sys.exit(1)
    
    if args.maxcycles < 1:
        print("Error: Maximum cycles must be positive", file=sys.stderr)
        sys.exit(1)

    # Find program file
    program_file_path = find_program_file(args.filename)
    
    if args.verbose:
        print(f"Program file: {program_file_path}")
        print(f"Debug mode: {args.debug}")
        print(f"Memory size: {args.memsize}")
        print(f"Max cycles: {args.maxcycles}")
    
    # Create and run simulator
    try:
        simulator = Simulator(
            program_filename=program_file_path,
            debug_mode=args.debug,
            memory_size=args.memsize,
            max_cycles=args.maxcycles
        )
        simulator.run()
        
    except Exception as e:
        import traceback
        print(f"Fatal error in simulator: {e}", file=sys.stderr)
        if args.verbose:
            traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()