CROSS := SIJIE
$(CROSS)_CC := $(ARMGCC_DIR)/bin/arm-none-eabi-gcc -mlittle-endian -mthumb -mcpu=cortex-m3 -march=armv7-m
$(CROSS)_CXX := $(ARMGCC_DIR)/bin/arm-none-eabi-g++	-mlittle-endian -mthumb -mcpu=cortex-m3 -march=armv7-m
$(CROSS)_OBJCOPY := $(ARMGCC_DIR)/bin/arm-none-eabi-objcopy
$(CROSS)_OBJDUMP := $(ARMGCC_DIR)/bin/arm-none-eabi-objdump

ifdef TWO_SHADOW_STACKS
$(CROSS)_LINKER_SCRIPT   ?= -T Imperas_TwoShadowStack.ld
else
$(CROSS)_LINKER_SCRIPT   ?= -T /workspace/cfed_basic/academiccasestudies/Imperas_withISR.ld
endif

$(CROSS)_LINKXX := $(ARMGCC_DIR)/bin/arm-none-eabi-g++ $($(CROSS)_LINKER_SCRIPT) -specs=nosys.specs