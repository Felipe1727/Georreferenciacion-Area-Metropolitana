"""Punto de entrada heredado: `python main.py` equivale a `python -m georef`.

El código está en el paquete `georef/`. `python main.py c` sigue funcionando como alias de
`python -m georef geocodificar`.
"""
from georef.cli import main

if __name__ == "__main__":
    main()
