# Linux: make CXX=g++; macOS Apple Clang: brew install libomp; make
CXX = c++
CPPFLAGS ?= -Iinclude
CXXFLAGS ?= -O3 -std=c++17 -Wall -Wextra -Wpedantic
LDFLAGS ?=
BUILD ?= build
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
  LIBOMP_PREFIX ?= /opt/homebrew/opt/libomp
  OMPFLAGS ?= -Xpreprocessor -fopenmp -I$(LIBOMP_PREFIX)/include
  OMPLIBS ?= -L$(LIBOMP_PREFIX)/lib -Wl,-rpath,$(LIBOMP_PREFIX)/lib -lomp
else
  OMPFLAGS ?= -fopenmp
  OMPLIBS ?= -fopenmp
endif
COMMON = $(BUILD)/graph.o $(BUILD)/pagerank.o
HEADERS = include/pagerank.hpp
.PHONY: all test sanitize clean
all: $(BUILD)/pagerank
$(BUILD):
	mkdir -p $@
$(BUILD)/%.o: src/%.cpp $(HEADERS) Makefile | $(BUILD)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(OMPFLAGS) '-DPR_BUILD_FLAGS="$(CXXFLAGS) $(OMPFLAGS)"' -MMD -MP -c $< -o $@
$(BUILD)/pagerank: $(COMMON) $(BUILD)/main.o
	$(CXX) $^ $(LDFLAGS) $(OMPLIBS) -o $@
$(BUILD)/test_pagerank: tests/test_pagerank.cpp $(COMMON) $(HEADERS) Makefile
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(OMPFLAGS) $< $(COMMON) $(LDFLAGS) $(OMPLIBS) -o $@
test: $(BUILD)/test_pagerank $(BUILD)/pagerank
	$(BUILD)/test_pagerank
	python3 tests/test_cli.py --binary $(BUILD)/pagerank
	python3 -m unittest discover -s tests -p 'test_scripts.py'
sanitize:
	$(MAKE) BUILD=build/sanitize CXXFLAGS='-O1 -g -std=c++17 -Wall -Wextra -Wpedantic -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='-fsanitize=address,undefined' test
clean:
	$(RM) -r $(BUILD)
-include $(wildcard $(BUILD)/*.d)
