# CSE312 - Semester Project: GTU-OS

## Description

GTU-OS is a small multithreaded operating system written entirely in assembly. It runs on GTU-C312, a hypothetical CPU that is simulated in Python. The OS keeps a thread table, schedules user threads with a cooperative round-robin scheduler, performs context switches, and handles system calls for printing, yielding, and halting. Three user threads (bubble sort, linear search, and Fibonacci) run on top of it and share the CPU.

This was the semester project for the Operating Systems course (CSE312) at Gebze Technical University, Spring 2025. The code in this repository is the version that was submitted.

## Program Structure and Features

### GTU-OS (`programs/operating_system.gtu312`)

*   **Memory Layout:**
    *   `0-20`: Memory-mapped CPU registers (`0` PC, `1` SP, `2` syscall result, `3` instruction count, `4` PC saved by `SYSCALL`).
    *   `21-99`: OS variables (current thread, active thread count, round-robin pointer, context-switch counter, etc.).
    *   `100-979`: Thread table, 11 entries of 80 words each.
    *   `1000+`: Thread `N` owns the block `N*1000 ... N*1000+999`. Its code starts at `N*1000` and its stack starts at the top of the block.

*   **Thread Table:** Each entry stores the thread ID, state (`READY`, `RUNNING`, `BLOCKED`, `HALTED`), saved PC, saved SP, first execution time, last start time, total executed instructions, the instruction count when it was last stopped, and its block duration. Thread 0 is the OS itself. The other 10 entries are user threads, and the OS initializes them at boot.

*   **Scheduler:** Cooperative round-robin. Starting from the thread after the last one that ran, the scheduler picks the next `READY` thread and skips the OS thread. Whenever it passes a `BLOCKED` thread, it checks whether 100 instructions have gone by since the thread was blocked, and if so marks it `READY` again. When no active threads remain, the OS records its own instruction usage and halts the CPU.

*   **Context Switch:** Saves the outgoing thread's state, PC, and SP to its table entry, updates its instruction accounting, and sets a block duration of 100 if the thread is being blocked. It then loads the incoming thread's PC and SP and enters user mode with the `USER` instruction.

*   **System Calls:** `SYSCALL` switches the CPU to kernel mode, saves the return PC to address `4`, and jumps to a fixed OS handler:

    | System Call | Handler | Effect on the calling thread |
    | :--- | :--- | :--- |
    | `SYSCALL YIELD` | `500` | Becomes `READY`; the scheduler picks the next thread. |
    | `SYSCALL HLT` | `550` | Becomes `HALTED`; the active thread count is decreased. |
    | `SYSCALL PRN A` | `600` | The simulator prints `M[M[A]]`, then the OS makes the thread `BLOCKED` for 100 instructions. |

### User Threads

*   **Thread 1 - Bubble Sort:** Sorts 10 integers in place, yields once, then prints the sorted array.
*   **Thread 2 - Linear Search:** Searches 8 integers for the key `42` and prints the index of its first occurrence.
*   **Thread 3 - Fibonacci:** Prints the first 10 Fibonacci numbers and yields once before its main loop.
*   **Threads 4-10:** Placeholder threads that call `SYSCALL HLT` right away, which shows that the OS can manage all 10 thread slots.

### GTU-C312 CPU Simulator (`gtu_cpu_simulatator/`)

*   **`main.py`:** Command-line entry point and the main simulation loop.
*   **`gtu_cpu.py`:** Fetch-decode-execute cycle, the instruction set (`SET`, `CPY`, `CPYI`, `CPYI2`, `ADD`, `ADDI`, `SUBI`, `JIF`, `PUSH`, `POP`, `CALL`, `RET`, `HLT`, `USER`, `SYSCALL`), and the debug dumps.
*   **`memory.py`:** Memory with kernel/user protection. User mode can only access addresses `1000` and above.
*   **`loader.py`:** Parses `.gtu312` files, which have a data section (`<address> <value>`) and an instruction section (`<number> <OPCODE> <operands>`).
*   **`instruction.py`, `utils.py`:** The instruction object, plus the CPU mode and thread state enums.

### Standalone Test Programs

These programs run directly on the CPU, without the OS, and leave their results in the final memory dump:

| Program | Result |
| :--- | :--- |
| `sample_program_pdf.gtu312` | The example from the assignment: sums 1 to 10, so `M[51] = 55`. |
| `bubble_sort_without_OS.gtu312` | Sorts the array at `M[60-69]`. |
| `linear_search_without_sort.gtu312` | Finds `42` at index `2` (`M[53]`). |
| `thread_table_init.gtu312` | Only the thread table initialization step. It stops at PC `100`, where the scheduler would begin. |

## Learning Objectives

*   **Thread Management:** Designing a thread table and handling transitions between thread states.
*   **CPU Scheduling:** Implementing cooperative round-robin scheduling, with blocked threads released after a time limit.
*   **Context Switching:** Saving and restoring thread state and switching between kernel and user mode.
*   **System Calls:** Trapping from user mode into fixed OS handlers.
*   **Memory Protection:** Separating kernel memory from user memory.
*   **Low-Level Programming:** Writing an OS and algorithms with a minimal instruction set and no general-purpose registers.
*   **Systems Simulation:** Building a CPU simulator with configurable debug output.

## How to Run

1.  **Prerequisites:** Python 3. No external packages are needed.

2.  **Run the OS** from the project root:
    ```bash
    ./execute.sh
    ```
    or directly:
    ```bash
    python3 gtu_cpu_simulatator/main.py programs/operating_system.gtu312 -D 0
    ```
    To change the debug level used by `execute.sh`, edit its `DEBUG` variable.

3.  **Debug Modes** (`-D`). All dumps are written to standard error.

    | Mode | Output |
    | :--- | :--- |
    | `0` | Runs the program, then dumps all non-zero memory. |
    | `1` | Dumps memory after every instruction. |
    | `2` | Same as `1`, but waits for Enter after each instruction. |
    | `3` | Dumps the thread table after every `USER` instruction and system call. |

    Optional flags: `--memsize` (default `20000`) and `--maxcycles` (default `500000`).

4.  **Expected Output:** The threads' output is interleaved, because every `SYSCALL PRN` blocks the printing thread and the scheduler moves on to the next ready thread:
    *   Thread 1: `11 12 23 34 45 56 67 78 89 90`
    *   Thread 2: `2`
    *   Thread 3: `0 1 1 2 3 5 8 13 21 34`

5.  **Run a standalone program:**
    ```bash
    python3 gtu_cpu_simulatator/main.py programs/sample_program_pdf.gtu312 -D 0
    ```

## AI Usage

The course required students to use AI tools during the project. They were used as a learning aid, not to complete the assignment for me. I asked about specific concepts to understand them, then designed and wrote the CPU and OS myself, and after that used AI to review the work and help find and fix problems. Any part the AI wrote was reviewed and corrected before it was used. The AI conversation was submitted with the assignment, but it is not published here for data-privacy reasons.

## Link to Details

*   [semester-project-report.pdf](semester-project-report.pdf): the full project report (design, implementation, and results for every debug mode).
*   [project-spring-2024-v2.pdf](project-spring-2024-v2.pdf): the assignment specification.
