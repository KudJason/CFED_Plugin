# Define output directory
OBJDIR := BUILD

# Move to the build directory
ifeq (,$(filter $(OBJDIR),$(notdir $(CURDIR))))
.SUFFIXES:
mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
MAKETARGET = '$(MAKE)' --no-print-directory -C $(OBJDIR) -f '$(mkfile_path)' \
		'SRCDIR=$(CURDIR)' $(MAKECMDGOALS) \
		'ALGORITHM_PATH=$(ALGORITHM_PATH)' \
		'FUNCTION=$(FUNCTION)' \
		'PROJECT=$(PROJECT)' \
		'CFED=$(CFED)' \
		'ALWAYS_REBUILD=1'
.PHONY: $(OBJDIR) clean
all:
	+@mkdir -p $(OBJDIR)
	+@$(MAKETARGET)

print-debug:
	@echo "PROJECT=$(PROJECT)"
	@echo "ALGORITHM_PATH=$(ALGORITHM_PATH)"
	@echo "FUNCTION=$(FUNCTION)"
	+@$(MAKETARGET) print-debug

$(OBJDIR): all
Makefile : ;
% :: $(OBJDIR) ;

else

# Print makefile information
$(info ** Entering main makefile build rules **)

###############################################################################
# Change these values per project
PROJECT?=BS
# Strip any file extension from PROJECT if present
PROJECT_NAME := $(basename $(notdir $(PROJECT)))
$(info ** Project from input: $(PROJECT), converted to: $(PROJECT_NAME) **)

ALGORITHM?=sortingAlgorithms
FUNCTION?=bubbleSort

# Handle algorithm path - check if it's absolute or relative
ALGORITHM_PATH?=/workspace/cfed_basic/academiccasestudies/$(PROJECT_NAME)/algorithms/$(ALGORITHM).cpp

# Debug information about paths
$(info ** Algorithm path: $(ALGORITHM_PATH) **)
$(info ** Project: $(PROJECT_NAME), Function: $(FUNCTION) **)

# # Enable CFED protection by default
CFED?=1
# Remove default values for these to ensure they come from command line
TECHNIQUE=
TECHNIQUE_TYPE=
SELECTIVE_LEVEL=

# Include additional plugin configuration
# -include /workspace/src/algorithm_compiler/plugin_config.mak

# Only print technique info if not being called from the build directory
ifeq (,$(filter $(OBJDIR),$(notdir $(CURDIR))))
$(info ** Using technique: TECHNIQUE=$(TECHNIQUE), TECHNIQUE_TYPE=$(TECHNIQUE_TYPE), SELECTIVE_LEVEL=$(SELECTIVE_LEVEL) **)
endif

###############################################################################

# Define include paths
INCLUDE_STARTUP = "/workspace/cfed_basic/academiccasestudies/startup"
INCLUDE_CMSIS = "/workspace/cfed_basic/academiccasestudies/CMSIS"

# Common compiler flags for ARM cross-compilation
COMMON_C = -I$(INCLUDE_STARTUP) -I$(INCLUDE_CMSIS) -I/workspace/cfed_basic/academiccasestudies/startup -O2 -g -std=gnu99 -c -mcpu=cortex-m3 -mthumb -march=armv7-m -fomit-frame-pointer -ffixed-r6 -fno-jump-tables -ffixed-r11 -ffixed-r10 -ffixed-r9
COMMON_CXX = -I$(INCLUDE_STARTUP) -I$(INCLUDE_CMSIS) -I/workspace/cfed_basic/academiccasestudies/startup -O2 -g -std=gnu++11 -c -mcpu=cortex-m3 -mthumb -march=armv7-m -fomit-frame-pointer -ffixed-r6 -fno-jump-tables -ffixed-r11 -ffixed-r10 -ffixed-r9

# Base objects required for all builds
OBJECTS = $(PROJECT_NAME).o

# Output file paths
OUTPUT_ELF := $(PROJECT_NAME).elf
OUTPUT_BIN := $(PROJECT_NAME).bin
OUTPUT_DISASM := $(PROJECT_NAME).disasm

# Set paths for plugin output to the current directory
CURDIR := $(shell pwd)
PLUGIN_OUTPUT_DIR := $(CURDIR)/GCC_Plugin_Output
$(shell mkdir -p $(PLUGIN_OUTPUT_DIR))
$(shell chmod -R 777 $(PLUGIN_OUTPUT_DIR))

# Set plugin paths and export environment variables
CFED_PLUGIN_PATH := /workspace/cfed_basic/cfed_plugin
DFED_PLUGIN_PATH := /workspace/cfed_basic/dfed_plugin
export CFED_PLUGIN_PATH
export GCC_PLUGIN_PATH := $(CFED_PLUGIN_PATH)
export GCC_PLUGIN_OUTPUT_DIR := $(PLUGIN_OUTPUT_DIR)

# Debug output to verify environment variables
$(info ** Current directory: $(CURDIR) **)
$(info ** Plugin output directory: $(PLUGIN_OUTPUT_DIR) **)
$(info ** Environment variables: GCC_PLUGIN_OUTPUT_DIR=$(GCC_PLUGIN_OUTPUT_DIR) **)
$(info ** Plugin path: $(CFED_PLUGIN_PATH) **)
$(info ** Plugin file exists: $(shell test -f $(CFED_PLUGIN_PATH)/CFED_plugin64.so && echo "yes" || echo "no") **)
$(info ** Plugin file permissions: $(shell ls -l $(CFED_PLUGIN_PATH)/CFED_plugin64.so) **)
$(info ** Plugin output directory permissions: $(shell ls -ld $(PLUGIN_OUTPUT_DIR)) **)

# Set ARMGCC_DIR
ARMGCC_DIR := /workspace/cfed_basic/toolchains/ARM/r5-r6
export ARMGCC_DIR

# Set CROSS variable for SIJIE
CROSS := SIJIE

# Include Sijie-specific configuration
-include /workspace/cfed_basic/academiccasestudies/Sijie_compile.mak

# Verify toolchain setup
ifeq ($($(CROSS)_CC),)
    $(error "Error : $(CROSS)_CC not set. Please check installation of toolchain for $(CROSS)")
endif

# Include plugin configuration if available
-include /workspace/src/algorithm_compiler/plugin_commands.mak

# Check if plugin command is defined
ifdef PLUGIN_COMMAND
    # Add plugin command to compiler flags
    COMMON_C += $(PLUGIN_COMMAND)
    COMMON_CXX += $(PLUGIN_COMMAND)
    $(info ** Added plugin command to compiler flags: $(PLUGIN_COMMAND) **)
    $(info ** Full compiler command: $($(CROSS)_CXX) $(COMMON_CXX) **)
endif

# CFED protection flag
# ifdef CFED
    #COMMON_C += -DCFED=$(CFED)
    #COMMON_CXX += -DCFED=$(CFED)
    #$(info ** CFED protection enabled ($(CFED)) **)
# endif


# Add technique-specific flags and objects if plugin is enabled
ifdef PLUGIN_COMMAND
    # Define SEL_LEVEL macro to match source code
    COMMON_C += -DTECHNIQUE=$(TECHNIQUE) -DTECH_TYPE=$(TECHNIQUE_TYPE) -DSELECTIVE_LEVEL=$(SELECTIVE_LEVEL) -DSEL_LEVEL=$(SELECTIVE_LEVEL)
    COMMON_CXX += -DTECHNIQUE=$(TECHNIQUE) -DTECH_TYPE=$(TECHNIQUE_TYPE) -DSELECTIVE_LEVEL=$(SELECTIVE_LEVEL) -DSEL_LEVEL=$(SELECTIVE_LEVEL)
    $(info ** Added technique configuration to compiler flags **)
    $(info ** TECHNIQUE: $(TECHNIQUE) **)
    $(info ** TECHNIQUE_TYPE: $(TECHNIQUE_TYPE) **)
    $(info ** SELECTIVE_LEVEL: $(SELECTIVE_LEVEL) **)
    
    ifeq (DETECTOR, $(TECHNIQUE))            ### DETECTOR ###
        TWO_SHADOW_STACKS=true
        COMMON_C += -DTWO_SHADOW_STACKS=$(TWO_SHADOW_STACKS) -ffixed-r5
        COMMON_CXX += -DTWO_SHADOW_STACKS=$(TWO_SHADOW_STACKS) -ffixed-r5
        OBJECTS += DETECTOR_compare.o
        $(info ** Added DETECTOR-specific flags and objects **)
    else ifeq (P-DETECTOR, $(TECHNIQUE))     ### P-DETECTOR ###
        OBJECTS += P-DETECTOR_parity.o
        $(info ** Added P-DETECTOR-specific flags and objects **)
    endif
endif

# Add system objects
OBJECTS += system_LPC17xx.o startup_LPC17xx.o

# Add output flag
COMMON_C += -o
COMMON_CXX += -o

# Print build configuration summary
$(info ** Build configuration summary **)
$(info ** OBJECTS: $(OBJECTS) **)
$(info ** COMMON_C: $(COMMON_C) **)
$(info ** COMMON_CXX: $(COMMON_CXX) **)

# Build rules for output files
ifdef GENERATE_BIN
$(OUTPUT_DISASM): $(OUTPUT_ELF) $(OUTPUT_BIN)
else
$(OUTPUT_DISASM): $(OUTPUT_ELF)
endif
	@echo "# Disassembling $(CROSS) $@" 
	@$($(CROSS)_OBJDUMP) -d -f -M reg-names-std --demangle "$(OUTPUT_ELF)" >"$(OUTPUT_DISASM)"
	@echo "Generated disassembly: $(OUTPUT_DISASM)"

$(OUTPUT_BIN): $(OUTPUT_ELF)
	@echo "# Creating binary $(CROSS) $@"
	@$($(CROSS)_OBJCOPY) -O binary "$(OUTPUT_ELF)" "$(OUTPUT_BIN)"
	@echo "Generated binary: $(OUTPUT_BIN)"

$(OUTPUT_ELF): $(OBJECTS)
	@echo "# Linking $(CROSS) $@"
	@echo "# Objects: $(OBJECTS)"
	$(V) $($(CROSS)_LINKXX) -o "$(OUTPUT_ELF)" $^ $($(CROSS)_LDFLAGS) -lstdc++ -lsupc++ -lm -lc -lgcc -mcpu=cortex-m3 -mthumb -march=armv7-m -Wl,--defsym=_shadowStack1=0x20000000 -Wl,--defsym=_shadowStack2=0x20001000 -Wl,--defsym=CFED_Detected=0
	@echo "Generated ELF: $(OUTPUT_ELF)"

# Build rule for the main project object
$(PROJECT_NAME).o: $(ALGORITHM_PATH)
	@echo "# Compiling $(PROJECT_NAME) from $(ALGORITHM_PATH)"
	@echo "# CFED protection enabled: $(CFED)"
	@echo "# Plugin command: $(PLUGIN_COMMAND)"
	@echo "# TECHNIQUE: $(TECHNIQUE), TECHNIQUE_TYPE: $(TECHNIQUE_TYPE), SELECTIVE_LEVEL: $(SELECTIVE_LEVEL)"
	@echo "# GCC_PLUGIN_OUTPUT_DIR: $(GCC_PLUGIN_OUTPUT_DIR)"
	@echo "# Output file: $@"
	@if [ ! -f "$(ALGORITHM_PATH)" ]; then \
		echo "ERROR: Source file $(ALGORITHM_PATH) does not exist!"; \
		exit 1; \
	fi
	@echo "# Environment variables:"
	@echo "# GCC_PLUGIN_PATH: $$GCC_PLUGIN_PATH"
	@echo "# GCC_PLUGIN_OUTPUT_DIR: $$GCC_PLUGIN_OUTPUT_DIR"
	@echo "# CFED_PLUGIN_PATH: $$CFED_PLUGIN_PATH"
	@echo "# Current directory: $$(pwd)"
	@echo "# Plugin file exists: $$(test -f $$CFED_PLUGIN_PATH/CFED_plugin64.so && echo "yes" || echo "no")"
	@echo "# Plugin output directory exists: $$(test -d $$GCC_PLUGIN_OUTPUT_DIR && echo "yes" || echo "no")"
	@echo "# Plugin output directory permissions: $$(ls -ld $$GCC_PLUGIN_OUTPUT_DIR)"
	$(V) $($(CROSS)_CXX) $(COMMON_CXX) $@ $(ALGORITHM_PATH)
	@echo "# Compilation of $(PROJECT_NAME).o completed"
	@echo "# Checking for plugin output..."
	@if [ -d "$(PLUGIN_OUTPUT_DIR)/$(FUNCTION)" ]; then \
		echo "✓ Plugin output directory for function $(FUNCTION) exists:"; \
		ls -la "$(PLUGIN_OUTPUT_DIR)/$(FUNCTION)"; \
	else \
		echo "✗ WARNING: No plugin output directory for function $(FUNCTION)!"; \
		echo "  This suggests the plugin did not run correctly."; \
		echo "  Current directory: $$(pwd)"; \
		echo "  Plugin output directory: $(PLUGIN_OUTPUT_DIR)"; \
		echo "  Plugin path: $(CFED_PLUGIN_PATH)"; \
		echo "  Plugin file exists: $$(test -f $(CFED_PLUGIN_PATH)/CFED_plugin64.so && echo "yes" || echo "no")"; \
		echo "  Plugin output directory exists: $$(test -d $(PLUGIN_OUTPUT_DIR) && echo "yes" || echo "no")"; \
		echo "  Plugin output directory permissions: $$(ls -ld $(PLUGIN_OUTPUT_DIR))"; \
		echo "  Available directories in plugin output:"; \
		if [ -d "$(PLUGIN_OUTPUT_DIR)" ]; then \
			ls -la "$(PLUGIN_OUTPUT_DIR)"; \
		else \
			echo "  (directory does not exist)"; \
		fi; \
	fi

# Build rules for additional objects
DETECTOR_compare.o: /workspace/cfed_basic/academiccasestudies/plugin_includes/DETECTOR_compare.s
	@echo "# Compiling $(CROSS) $<"
	@$(V) $($(CROSS)_CC) $(COMMON_C) $@ $< 

P-DETECTOR_parity.o: /workspace/cfed_basic/academiccasestudies/plugin_includes/P-DETECTOR_parity.s
	@echo "# Compiling $(CROSS) $<"
	@$(V) $($(CROSS)_CC) $(COMMON_C) $@ $< 
	
# Build rules for startup files
ifdef TWO_SHADOW_STACKS
startup_LPC17xx.o: /workspace/cfed_basic/academiccasestudies/startup/startup_LPC17xx_OVPsim_TwoShadowStack.s
	@echo "# Compiling $(CROSS) $<"
	@$(V) $($(CROSS)_CC) $(COMMON_C) $@ $< 
else
startup_LPC17xx.o: /workspace/cfed_basic/academiccasestudies/startup/startup_LPC17xx_OVPsim.s
	@echo "# Compiling $(CROSS) $<"
	@$(V) $($(CROSS)_CC) $(COMMON_C) $@ $< 
endif

system_LPC17xx.o: /workspace/cfed_basic/academiccasestudies/startup/system_LPC17xx.c
	@echo "# Compiling $(CROSS) $<"
	@$(V) $($(CROSS)_CC) $(COMMON_C) $@ $< 

# Main target - first target defined is the default
.PHONY: all verify-plugin
all: check-rebuild $(OUTPUT_DISASM) verify-plugin
	@echo "======== Build completed successfully ========"
	@echo "  ELF: $(OUTPUT_ELF)"
	@echo "  BIN: $(OUTPUT_BIN)"
	@echo "  DISASM: $(OUTPUT_DISASM)"
	@echo "  Plugin Output: $(PLUGIN_OUTPUT_DIR)"
	@ls -la

# Check if we need to force a rebuild
.PHONY: check-rebuild
check-rebuild:
ifdef ALWAYS_REBUILD
	@echo "Forcing rebuild..."
	@rm -f $(PROJECT_NAME).o $(OUTPUT_ELF) $(OUTPUT_BIN) $(OUTPUT_DISASM)
endif

# Target to verify plugin execution
verify-plugin:
	@echo "======== Verifying Plugin Execution ========"
	@if [ -n "$$(ls -A $(GCC_PLUGIN_OUTPUT_DIR))" ]; then \
		echo "✓ Plugin output directory contains files or directories"; \
	else \
		echo "✗ Plugin output directory is empty"; \
	fi
	@echo "=========================================="

# Target to print all debug info
print-debug:
	@echo "======== Makefile Debug Information ========"
	@echo "PROJECT: $(PROJECT)"
	@echo "PROJECT_NAME: $(PROJECT_NAME)"
	@echo "ALGORITHM_PATH: $(ALGORITHM_PATH)"
	@echo "FUNCTION: $(FUNCTION)"
	@echo "CFED: $(CFED)"
	@echo "TECHNIQUE: $(TECHNIQUE)"
	@echo "TECHNIQUE_TYPE: $(TECHNIQUE_TYPE)"
	@echo "SELECTIVE_LEVEL: $(SELECTIVE_LEVEL)"
	@echo "PLUGIN_COMMAND: $(PLUGIN_COMMAND)"
	@echo "GCC_PLUGIN_OUTPUT_DIR: $(GCC_PLUGIN_OUTPUT_DIR)"
	@echo "OBJECTS: $(OBJECTS)"
	@echo "Current directory: $(CURDIR)"
	@echo "=========================================="

# Add better error handling for algorithm path
ifeq ($(wildcard $(ALGORITHM_PATH)),)
    $(info ** WARNING: Algorithm file $(ALGORITHM_PATH) does not exist! **)
endif

# Ensure FUNCTION is set correctly
ifeq ($(FUNCTION),)
    $(info ** ERROR: FUNCTION must be specified! **)
    $(error FUNCTION is not specified)
endif

endif

# Clean target to remove build artifacts
clean:
	@echo "Deleting previous build"
	@rm -rf $(OBJDIR)
	@rm -rf GCC_Plugin_Output
	@echo "Clean completed"
