#!/usr/bin/env python3
"""Concatenate LinkML schema components into a complete schema."""

import sys
from pathlib import Path

output = sys.argv[1] if len(sys.argv) > 1 else 'entire_schema.yml'

with open(output, 'w') as out:
    # Schema metadata
    out.write(Path('other_elements/schema_metadata.yml').read_text())
    out.write('\n')
    
    # Enums
    out.write(Path('other_elements/enums.yml').read_text())
    out.write('\n')
    
    # Classes
    out.write(Path('other_elements/classes.yml').read_text())
    out.write('\n')
    
    # Slots
    out.write('################################################################################\n')
    out.write('# SLOTS - FIELD DEFINITIONS\n')
    out.write('# Here is where we describe the column names from MOB data and conceptually\n')
    out.write('# map them to DwC\n')
    out.write('################################################################################\n')
    out.write('\n')
    out.write('slots:\n')
    for slot_file in sorted(Path('slots').glob('*.yaml')):
        for line in slot_file.read_text().splitlines():
            out.write(f'  {line}\n' if line.strip() else '\n')
        out.write('\n')  # blank line between slots

print(f'Schema written to {output}')
