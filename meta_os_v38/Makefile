CC ?= gcc
CFLAGS ?= -O3 -march=native -std=c11 -Wall -Wextra -Werror
CPPFLAGS += -Iinclude
LDLIBS += -llz4 -lz

all: metaram_bench

metaram_bench: src/metaram.c bench/metaram_bench.c include/metaram.h
	$(CC) $(CPPFLAGS) $(CFLAGS) src/metaram.c bench/metaram_bench.c -o $@ $(LDLIBS)

clean:
	rm -f metaram_bench
