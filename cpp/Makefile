CXX ?= clang++
CXXFLAGS = -O3 -std=c++17 -Wall -Wextra -fPIC -Iinclude

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
    DYLIB_EXT = dylib
    SHARED_FLAG = -dynamiclib
else
    DYLIB_EXT = so
    SHARED_FLAG = -shared
endif

TARGET_LIB = libfraud_evaluator.$(DYLIB_EXT)
BENCHMARK_BIN = benchmark_runner

all: $(TARGET_LIB) $(BENCHMARK_BIN)

$(TARGET_LIB): src/fraud_evaluator.cpp include/fraud_evaluator.h
	$(CXX) $(CXXFLAGS) $(SHARED_FLAG) -o $@ src/fraud_evaluator.cpp

$(BENCHMARK_BIN): src/main_benchmark.cpp src/fraud_evaluator.cpp include/fraud_evaluator.h
	$(CXX) $(CXXFLAGS) -o $@ src/main_benchmark.cpp src/fraud_evaluator.cpp

clean:
	rm -f $(TARGET_LIB) $(BENCHMARK_BIN) *.o

.PHONY: all clean
