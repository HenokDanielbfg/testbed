# script.py

import sys

def greet(name):
    return f"Hello, {name}!"

if __name__ == "__main__":
    # Read the name from command-line arguments
    name = sys.argv[1] if len(sys.argv) > 1 else "World"
    print(greet(name))

