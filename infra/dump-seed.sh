#!/usr/bin/env bash
# Dump the current database seed data to infra/seed.sql
# Run from repo root: bash infra/dump-seed.sh
set -euo pipefail

DB_URL="${DATABASE_URL:-postgresql://roadsos:roadsos@localhost:5432/roadsos}"
OUTPUT="infra/seed.sql"

echo "Dumping seed data from $DB_URL to $OUTPUT..."

# Dump emergency_services and protocol_chunks tables (seed data only, no user data)
psql "$DB_URL" -c "\COPY (SELECT * FROM emergency_services ORDER BY id) TO STDOUT WITH CSV HEADER" > "$OUTPUT.tmp1" 2>/dev/null || true
psql "$DB_URL" -c "\COPY (SELECT * FROM protocol_chunks ORDER BY id) TO STDOUT WITH CSV HEADER" > "$OUTPUT.tmp2" 2>/dev/null || true

# Generate INSERT statements from the Python seed data
python3 -c "
import sys
sys.path.insert(0, 'backend')
from app.seed.gen_sql import generate_sql
sql = generate_sql()
with open('$OUTPUT', 'w', encoding='utf-8') as f:
    f.write(sql)
print('Generated $OUTPUT (' + str(len(sql)) + ' bytes)')
"

rm -f "$OUTPUT.tmp1" "$OUTPUT.tmp2"
echo "Done. Seed data written to $OUTPUT"