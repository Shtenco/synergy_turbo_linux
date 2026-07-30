CC ?= gcc
BUILD_DIR := build
RESULTS_DIR := results
INCLUDES := -Iinclude
COMMON_CFLAGS := -O3 -std=c11 -Wall -Wextra -Werror -fno-plt -fno-semantic-interposition
COMMON_LDFLAGS :=
SOURCES := src/core.c bench/turbo_bench.c

.PHONY: all clean test bench bench-baseline bench-native freestanding

all: $(BUILD_DIR)/turbo-bench-baseline $(BUILD_DIR)/turbo-bench-native

$(BUILD_DIR):
	mkdir -p $@

$(RESULTS_DIR):
	mkdir -p $@

$(BUILD_DIR)/turbo-bench-baseline: $(SOURCES) | $(BUILD_DIR)
	$(CC) $(COMMON_CFLAGS) -march=x86-64 -mtune=generic $(INCLUDES) $^ -o $@ $(COMMON_LDFLAGS)

$(BUILD_DIR)/turbo-bench-native: $(SOURCES) | $(BUILD_DIR)
	$(CC) $(COMMON_CFLAGS) -march=native -mtune=native $(INCLUDES) $^ -o $@ $(COMMON_LDFLAGS)

$(BUILD_DIR)/core-freestanding.o: src/core.c | $(BUILD_DIR)
	$(CC) -O3 -std=c11 -Wall -Wextra -Werror -ffreestanding -fno-stack-protector \
		-fno-pie -mno-red-zone -mcmodel=kernel -march=x86-64 $(INCLUDES) -c $< -o $@

test: $(BUILD_DIR)/turbo-bench-baseline $(BUILD_DIR)/core-freestanding.o
	./$(BUILD_DIR)/turbo-bench-baseline --self-test

bench-baseline: $(BUILD_DIR)/turbo-bench-baseline | $(RESULTS_DIR)
	./$(BUILD_DIR)/turbo-bench-baseline --json | tee $(RESULTS_DIR)/baseline.json

bench-native: $(BUILD_DIR)/turbo-bench-native | $(RESULTS_DIR)
	./$(BUILD_DIR)/turbo-bench-native --json | tee $(RESULTS_DIR)/native.json

bench: bench-baseline bench-native

freestanding: $(BUILD_DIR)/core-freestanding.o

clean:
	rm -rf $(BUILD_DIR) $(RESULTS_DIR)
