from .utils import short_id
from contextlib import contextmanager
import tokenize
import io


class MagicParser:

    def __init__(self):
        self._placeholders={}
        self._placeholder_stack=[]

    def _parse_system_cmd(self, code):
        """Parses and transforms system commands in the code.
        Args:
            code (str): The input code containing potential system commands.
        Returns:
            str: The transformed code with system commands replaced by function calls.
        """
        stripped_code=code.lstrip('\n')
        if stripped_code.startswith('!!'):
            command = stripped_code[2:].lstrip('\n')
            id= short_id()
            self._placeholders[id]=command
            return f"__shell__.run_system_cmd(__shell__._magic_parser._placeholders.get('{id}'))"

        lines = code.split('\n')
        ignore_map = self._build_ignore_map(code, lines)
        for i, line in enumerate(lines):
            stripped_line = line.lstrip()
            if stripped_line.startswith('!') and not stripped_line.startswith('!!'):
                column = len(line) - len(stripped_line)
                if self._position_ignored(ignore_map, i + 1, column):
                    continue
                indent = line[:column]
                command = stripped_line[1:].lstrip()
                id= short_id()
                self._placeholders[id]=command
                
                lines[i] = f"{indent}__shell__.run_system_cmd(__shell__._magic_parser._placeholders.get('{id}'))"
        return '\n'.join(lines)

    def _parse_magics(self,code):
        """Parses and transforms magic commands in the code.
        Args:
            code (str): The input code containing potential magic commands.
        Returns:
            str: The transformed code with magic commands replaced by function calls.
        """
        stripped_code=code.lstrip('\n')
        if stripped_code.startswith('%%'):
            lines=stripped_code.split('\n')
            magic=lines[0][2:].strip()
            content='\n'.join(lines[1:])
            id= short_id()
            self._placeholders[id]=content
            code=f"__magics__['{magic}'](__shell__._magic_parser._placeholders.get('{id}'))"
        else:
            lines=code.split('\n')
            ignore_map = self._build_ignore_map(code, lines)
            for i,line in enumerate(lines):
                stripped=line.lstrip()
                if stripped.startswith("%"):
                    column=len(line)-len(stripped)
                    if self._position_ignored(ignore_map, i + 1, column):
                        continue
                    indent=line[:column]
                    parts=stripped.split(" ",1)
                    magic=parts[0][1:]
                    content=parts[1].strip() if len(parts)>1 else ""
                    id= short_id()
                    self._placeholders[id]=content
                    lines[i]=f"{indent}__magics__['{magic}'](__shell__._magic_parser._placeholders.get('{id}'))"
            code='\n'.join(lines)
        return code

    @contextmanager
    def _placeholder_scope(self):
        """
        Provides an isolated placeholder store for a single shell run.

        A stack is used so nested shell runs (e.g. magics invoking __shell__.run)
        keep their placeholders separate.
        """
        previous = getattr(self, "_placeholders", {})
        self._placeholder_stack.append(previous)
        self._placeholders = {}
        try:
            yield self._placeholders
        finally:
            prior = self._placeholder_stack.pop() if self._placeholder_stack else {}
            self._placeholders = prior if prior is not None else {}

    @staticmethod
    def _position_ignored(ignore_map, line_no, column):
        """Checks if a given position is within an ignored range.
        Args:
            ignore_map (dict): The ignore map.
            line_no (int): The line number (1-based).
            column (int): The column number (0-based).
        Returns:
            bool: True if the position is ignored, False otherwise.
        """
        for start, end in ignore_map.get(line_no, ()):
            if start <= column < end:
                return True
        return False
    
    def _build_ignore_map(self, code, lines):
        """Builds a map of positions to ignore (inside strings or comments).
        Used to avoid parsing magics or system commands inside strings or comments.
        Args:
            code (str): The input code.
            lines (list): List of lines in the code.
        Returns:
            dict: A mapping of line numbers to lists of (start_col, end_col) tuples to ignore.
        """
        ignore = {}
        try:
            tokens = tokenize.generate_tokens(io.StringIO(code).readline)
        except (tokenize.TokenError, IndentationError):
            return ignore

        for tok in tokens:
            if tok.type in (tokenize.STRING, tokenize.COMMENT):
                (start_line, start_col) = tok.start
                (end_line, end_col) = tok.end

                if start_line == end_line:
                    ignore.setdefault(start_line, []).append((start_col, end_col))
                else:
                    line_text = lines[start_line - 1] if start_line - 1 < len(lines) else ''
                    ignore.setdefault(start_line, []).append((start_col, len(line_text)))
                    for line in range(start_line + 1, end_line):
                        line_text = lines[line - 1] if line - 1 < len(lines) else ''
                        ignore.setdefault(line, []).append((0, len(line_text)))
                    ignore.setdefault(end_line, []).append((0, end_col))

        return ignore