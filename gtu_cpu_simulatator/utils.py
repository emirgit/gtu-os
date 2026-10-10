from enum import Enum, auto

class CPUMode(Enum):
    KERNEL = auto()
    USER = auto()

class ThreadState(Enum):
    READY = auto()
    RUNNING = auto()
    BLOCKED = auto()
    HALTED = auto()