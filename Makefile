# Define variables
MPY_CROSS = /home/cnd/Downloads/repos/micropython/mpy-cross/build/mpy-cross
SRC = toml.py
OUT = toml124.mpy

# Default target
all: $(OUT)

# Rule to create .mpy from .py
$(OUT): $(SRC)
	$(MPY_CROSS) $(SRC) -o $(OUT)

# Clean up
clean:
	rm -f $(OUT)

# Phony targets
.PHONY: all clean

