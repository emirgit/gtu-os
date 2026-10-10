# gtu_cpu_simulator/memory.py
from typing import Dict
from utils import CPUMode

class MemoryAccessError(Exception):
    """Raised when there's an invalid memory access"""
    def __init__(self, message: str, address: int, mode: CPUMode):
        super().__init__(message)
        self.address = address
        self.mode = mode

class MemoryManager:
    """Manages CPU memory with access controls"""
    
    USER_MEMORY_START = 1000  # USER mode can only access addresses >= 1000
    
    def __init__(self, size: int = 20000):
        self.size = size
        self.memory: Dict[int, int] = {}  # Sparse memory representation
        
    def _check_bounds(self, address: int) -> bool:
        """Check if address is within memory bounds"""
        return 0 <= address < self.size
    
    def _check_access_permission(self, address: int, mode: CPUMode) -> bool:
        """Check if the current mode can access the given address"""
        if mode == CPUMode.KERNEL:
            return True  # Kernel mode can access everything
        elif mode == CPUMode.USER:
            return address >= self.USER_MEMORY_START  # User mode restricted
        return False
    
    def read(self, address: int, mode: CPUMode) -> int:
        """Read value from memory with access control"""
        if not self._check_bounds(address):
            raise MemoryAccessError(f"Memory read out of bounds", address, mode)
        
        if not self._check_access_permission(address, mode):
            raise MemoryAccessError(f"Access denied in {mode.name} mode", address, mode)
        
        
        return self.memory.get(address, 0)  # Return 0 for uninitialized memory
    
    def write(self, address: int, value: int, mode: CPUMode):
        """Write value to memory with access control"""
        if not self._check_bounds(address):
            raise MemoryAccessError(f"Memory write out of bounds", address, mode)
        
        if not self._check_access_permission(address, mode):
            raise MemoryAccessError(f"Write access denied in {mode.name} mode", address, mode)
        
        self.memory[address] = value
    
    def get_value_unchecked(self, address: int) -> int:
        """Get value without access control (for system operations)"""
        if not self._check_bounds(address):
            return 0
        return self.memory.get(address, 0)
    
    def set_value_unchecked(self, address: int, value: int):
        """Set value without access control (for system operations)"""
        if self._check_bounds(address):
            self.memory[address] = value
    
    def get_all_non_zero(self) -> Dict[int, int]:
        """Return all non-zero memory locations"""
        return {addr: val for addr, val in self.memory.items() if val != 0}