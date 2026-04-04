from __future__ import annotations

import argparse
from src.cobol_ast_trace import load_program
from src.program.programm import Programm



def main2():

    ap = argparse.ArgumentParser()
    ap.add_argument('cbl', nargs='?', help='Path to .cbl file for path tracing')
    ap.add_argument('--entry', default=None, help='Entry paragraph')
    ap.add_argument('--vars', nargs='*', default=[], help='Initial vars like A=1 B="X" FLAG=true')
    ap.add_argument('--copy-dirs', nargs='*', default=[], help='Directories where copybooks are searched')
    ap.add_argument('--copy-exts', nargs='*', default=['', '.cpy', '.CPY', '.copy', '.COPY'], help='Copybook extensions to try')
    ap.add_argument('--max-steps', type=int, default=3000)
    ap.add_argument('--max-paths', type=int, default=80)
    ap.add_argument('--json', action='store_true', help='Output NDJSON (one path per line)')
    ap.add_argument('--debug', action='store_true', help='Verbose parser/tracer output')

    ap.add_argument('--root-dir', help='Root COBOL directory for program indexing / call graph generation')
    ap.add_argument('--entry-program-id', help='Entry PROGRAM-ID for recursive call graph building')
    ap.add_argument('--graph-json', help='Write reachable call graph as JSON')
    ap.add_argument('--graph-svg', help='Write reachable call graph as SVG')
    ap.add_argument('--list-programs', action='store_true', help='List indexed PROGRAM-ID values')

    args = ap.parse_args()

    programm: Programm = load_program(args.cbl)
    programm.parse()
    print(programm)

if __name__ == '__main__':
    main2()
