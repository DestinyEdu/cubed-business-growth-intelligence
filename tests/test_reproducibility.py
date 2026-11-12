import hashlib
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BUILD_SCRIPT = """
import sys
from pathlib import Path
import src.create_database as cd
import src.generate_data as gd
p = Path(sys.argv[1])
cd.DB_PATH = p
gd.DB_PATH = p
gd.main()
"""


def build(path):
    subprocess.run([sys.executable, "-c", BUILD_SCRIPT, str(path)],
                   cwd=ROOT, check=True, capture_output=True)


def fingerprint(path):
    conn = sqlite3.connect(path)
    h = hashlib.sha256()
    for line in conn.iterdump():
        h.update(line.encode())
    conn.close()
    return h.hexdigest()


def test_generator_is_reproducible(tmp_path):
    a, b = tmp_path / "a.db", tmp_path / "b.db"
    build(a)
    build(b)
    assert fingerprint(a) == fingerprint(b)
