"""PyInstaller entry point for the standalone sifty.exe.

PyInstaller runs the entry script as a top-level ``__main__`` with no parent
package, so it must use an **absolute** import (``src/sifty/__main__.py`` uses
a relative one for ``python -m sifty`` and can't be the PyInstaller entry).
Build with ``--paths src`` so ``sifty`` is importable.
"""

from sifty.cli.app import entrypoint

if __name__ == "__main__":
    entrypoint()
