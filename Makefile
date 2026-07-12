CXX ?= g++
PYTHON ?= python3
CXXFLAGS := -std=c++20 -O2 -pipe -Wall -Wextra -Wshadow -Wconversion -Wno-sign-conversion
BUILD_DIR := build

.PHONY: build run test judge clean

build:
	@test -n "$(FILE)" || (echo "Use: make run FILE=caminho/solucao.cpp"; exit 2)
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) "$(FILE)" -o $(BUILD_DIR)/solution

run: build
	$(BUILD_DIR)/solution

test: build
	@test -n "$(INPUT)" || (echo "Use: make test FILE=solucao.cpp INPUT=caso.in EXPECTED=caso.out"; exit 2)
	@test -n "$(EXPECTED)" || (echo "Use: make test FILE=solucao.cpp INPUT=caso.in EXPECTED=caso.out"; exit 2)
	$(BUILD_DIR)/solution < "$(INPUT)" > "$(BUILD_DIR)/actual.out"
	diff -u "$(EXPECTED)" "$(BUILD_DIR)/actual.out"

judge:
	@test -n "$(FILE)" || (echo "Use: make judge FILE=solucao.cpp PACKAGE=pacote.tar PROBLEM=A"; exit 2)
	@test -n "$(PACKAGE)" || (echo "Use: make judge FILE=solucao.cpp PACKAGE=pacote.tar PROBLEM=A"; exit 2)
	@test -n "$(PROBLEM)" || (echo "Use: make judge FILE=solucao.cpp PACKAGE=pacote.tar PROBLEM=A"; exit 2)
	$(PYTHON) tools/judge_sbc.py --file "$(FILE)" --package "$(PACKAGE)" --problem "$(PROBLEM)" $(JUDGE_ARGS)

clean:
	rm -rf $(BUILD_DIR)
