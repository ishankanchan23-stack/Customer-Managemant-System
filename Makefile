CXX      = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -I.
TARGET   = cms

SRC = main.cpp Customer.cpp
OBJ = $(SRC:.cpp=.o)

all: $(TARGET)

$(TARGET): $(OBJ)
	$(CXX) $(CXXFLAGS) -o $@ $^

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

run: $(TARGET)
	./$(TARGET)

web:
	python server.py

test:
	python -m unittest discover -s tests -v

clean:
	rm -f $(OBJ) $(TARGET)

.PHONY: all run web test clean
