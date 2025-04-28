# CFED Plugin Configuration
$(info ** Including plugin commands configuration **)

# Dummy target
.PHONY: plugin-config
plugin-config:
	@echo "Plugin configuration loaded"

# Initialize plugin command variable
PLUGIN_COMMAND :=

# CFED plugin configuration
ifdef CFED
    # Verify plugin file exists
    ifeq ($(wildcard $(CFED_PLUGIN_PATH)/CFED_plugin64.so),)
        $(error "CFED plugin file not found at $(CFED_PLUGIN_PATH)/CFED_plugin64.so")
    endif
    
    # Base plugin command
    PLUGIN_COMMAND += -fplugin=$(CFED_PLUGIN_PATH)/CFED_plugin64.so -ffixed-r6
    
    # Add function argument if specified
    ifneq ($(FUNCTION),)
        PLUGIN_COMMAND += -fplugin-arg-CFED_plugin64-function=$(FUNCTION)
        $(info ** Added function argument: $(FUNCTION) **)
    endif
    
    # Add technique type argument if specified
    ifneq ($(TECHNIQUE_TYPE),)
        PLUGIN_COMMAND += -fplugin-arg-CFED_plugin64-techniqueType=$(TECHNIQUE_TYPE)
        $(info ** Added technique type argument: $(TECHNIQUE_TYPE) **)
    endif
    
    # Add technique specific argument if specified
    ifneq ($(TECHNIQUE),)
        PLUGIN_COMMAND += -fplugin-arg-CFED_plugin64-techniqueSpecific=$(TECHNIQUE)
        $(info ** Added technique specific argument: $(TECHNIQUE) **)
    endif
    
    # Add selective level argument if specified
    ifneq ($(SELECTIVE_LEVEL),)
        PLUGIN_COMMAND += -fplugin-arg-CFED_plugin64-selectiveLevel=$(SELECTIVE_LEVEL)
        $(info ** Added selective level argument: $(SELECTIVE_LEVEL) **)
    endif
    
    $(info ** Final CFED plugin command: $(PLUGIN_COMMAND) **)
endif

# DFED plugin configuration
ifdef DFED
    # Verify plugin file exists
    ifeq ($(wildcard $(DFED_PLUGIN_PATH)/DFED_plugin64.so),)
        $(error "DFED plugin file not found at $(DFED_PLUGIN_PATH)/DFED_plugin64.so")
    endif
    
    PLUGIN_COMMAND += -fplugin=$(DFED_PLUGIN_PATH)/DFED_plugin64.so -ffixed-r6
    $(info ** DFED plugin enabled: $(PLUGIN_COMMAND) **)
endif