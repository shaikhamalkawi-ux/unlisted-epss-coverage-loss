from pathlib import Path
import csv,hashlib
root=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((root/'SHA256_MANIFEST.csv').open()))
for row in rows:
    p=root/row['path']
    assert p.is_file(), f"Missing: {p}"
    assert p.stat().st_size==int(row['bytes']), f"Length mismatch: {p}"
    assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'], f"Hash mismatch: {p}"
print(f'PASS: {len(rows)} manifest payloads')
