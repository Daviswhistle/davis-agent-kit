#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys

def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Merge translation markdown or HTML chunks into a single unified file in correct order.")
    parser.add_argument("--input-dir", required=True, help="Directory containing translation chunk files")
    parser.add_argument("--output", required=True, help="Path to write the combined output file")
    parser.add_argument("--title", help="Optional document title to prepend")
    parser.add_argument("--description", help="Optional document description to prepend")
    return parser.parse_args(argv)

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_path = Path(args.input_dir)
    output_path = Path(args.output)

    if not input_path.exists() or not input_path.is_dir():
        print(f"ERROR: input directory does not exist or is not a directory: {args.input_dir}", file=sys.stderr)
        return 2

    # Gather and sort chunk files numerically/alphabetically
    chunk_files = sorted(input_path.glob("*.md"))
    if not chunk_files:
        chunk_files = sorted(input_path.glob("*.html"))
        if not chunk_files:
            chunk_files = sorted(input_path.glob("*.txt"))

    if not chunk_files:
        print(f"ERROR: no .md, .html, or .txt files found in {args.input_dir}", file=sys.stderr)
        return 2

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as outfile:
        if args.title:
            outfile.write(f"# {args.title}\n\n")
        if args.description:
            outfile.write(f"{args.description}\n\n---\n\n")

        for idx, chunk in enumerate(chunk_files):
            print(f"Merging [{idx+1}/{len(chunk_files)}]: {chunk.name}...")
            content = chunk.read_text(encoding="utf-8")
            outfile.write(content)
            outfile.write("\n\n---\n\n")

    print(f"Successfully merged {len(chunk_files)} chunks into {args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
