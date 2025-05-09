import sys
import os

def main():
    # Kontrollera att alla __init__.py finns
    missing = []
    base = os.path.dirname(__file__)
    for sub in ['', 'static', 'scripts', 'tests', 'archive']:
        path = os.path.join(base, sub, '__init__.py')
        if not os.path.isfile(path):
            missing.append(path)
    if missing:
        print(f"Saknar __init__.py i: {missing}")
        sys.exit(1)
    print("Alla __init__.py finns!")

if __name__ == "__main__":
    main()
