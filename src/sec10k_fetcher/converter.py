from __future__ import annotations

from sec2md import Parser


def convert_to_full_markdown(html_content: str) -> str:
    parser = Parser(html_content)
    return parser.markdown()
