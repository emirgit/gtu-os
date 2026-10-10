#!/bin/bash

# Path to the operating system program
PROGRAM="programs/operating_system.gtu312"

# Path to python cpu simulator
SIMULATOR="gtu_cpu_simulatator/main.py"

# Debug (0,1,2,3)
DEBUG=0

# If the script doesn't work, you can run from project folder like this:
# python3 gtu_cpu_simulatator/main.py programs/operating_system.gtu312
# If you change the debug level, add -D <debug_level> to the command

echo "=== Running GTU-C312 CPU Simulator ==="
echo "Program : $PROGRAM"
echo "Simulator: $SIMULATOR"
echo "Debug Level: $DEBUG"
echo "======================================"

python3 $SIMULATOR $PROGRAM -D $DEBUG

echo "======================================"
echo "Execution finished."
