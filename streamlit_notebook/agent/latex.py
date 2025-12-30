import re
from .stream_utils import Streamer, TokenStreamer, fenced

def escape_formula_specials(formula: str) -> str:
    """
    Dans une formule KaTeX, on veut transformer uniquement les séquences
    d'escape type JSON/Python :

        \n, \t, \r, \b, \f, \", \'

    en :

        \\n, \\t, \\r, \\b, \\f, \\", \'

    SANS toucher :
      - aux séquences déjà échappées (\\n, \\t, ...)
      - aux commandes LaTeX (\frac, \alpha, \begin, ...)
      - aux brackets ()[]{} et autres structures KaTeX.
    """

    # 1) Contrôles \n \t \r \b \f
    # On ne touche que les séquences \x non suivies d'une autre lettre
    # pour éviter \frac, \begin, etc.
    control_chars = "ntrbf"
    pattern_controls = re.compile(
        rf'(?<!\\)\\([{control_chars}])(?=$|[^A-Za-z])'
    )
    formula = pattern_controls.sub(r'\\\1', formula)

    # 2) Quotes : \" et \'
    pattern_quotes = re.compile(r'(?<!\\)\\(["\'])')
    formula = pattern_quotes.sub(r'\\\1', formula)

    return formula

def _normalize_latex_delimiters(text: str) -> str:
    """
    Convertit :
      \( ... \)  ->  $...$
      \[ ... \]  ->  $$...$$

    - Sur une seule ligne (pas de \n à l'intérieur)
    - On supporte les backslashes normaux type LLM / JSON.
    """

    # Display math : \[ ... \]  ->  $$ ... $$
    text = re.sub(
        r'(?<!\\)\\\[(?P<disp>[^\]\n]+?)\\\]',   # \[ ... \]
        lambda m: f"$${m.group('disp')}$$",
        text,
    )

    # Inline math : \( ... \)  ->  $ ... $
    text = re.sub(
        r'(?<!\\)\\\((?P<inl>[^\)\n]+?)\\\)',    # \( ... \)
        lambda m: f"${m.group('inl')}$",
        text,
    )

    return text

def _escape_katex_formulas(text: str) -> str:
    """
    Traite uniquement les formules KaTeX dans `text` (hors blocs de code).

    Gère :
      - block triple ligne :  $$ \n ... \n $$
      - display inline :     $$ ... $$
      - inline :             $ ... $
    """

    # D'abord normaliser \(..\) et \[..\] en $..$ / $$..$$
    text = _normalize_latex_delimiters(text)

    pattern = re.compile(
        r"""
        # 1) Bloc KaTeX sur plusieurs lignes :
        (?P<block>^\s*\$\$\s*\n(?P<block_content>.*?)(?:\n)?\s*\$\$\s*$)
        |
        # 2) Inline display : $$...$$ sur une seule ligne
        (?P<inline_display>(?<!\$)\$\$(?!\$)(?P<inline_display_content>[^\n$]+?)\$\$(?!\$))
        |
        # 3) Inline normal : $...$ sur une seule ligne
        (?P<inline>(?<!\$)\$(?!\$)(?P<inline_content>[^$\n]+?)\$(?!\$))
        """,
        re.VERBOSE | re.DOTALL | re.MULTILINE,
    )

    def repl(match: re.Match) -> str:
        # Bloc multi-ligne
        if match.group("block_content") is not None:
            content = match.group("block_content")
            return "$$\n" + escape_formula_specials(content) + "\n$$"

        # Inline display $$...$$
        if match.group("inline_display_content") is not None:
            content = match.group("inline_display_content")
            return f"$${escape_formula_specials(content)}$$"

        # Inline $...$
        content = match.group("inline_content")
        return f"${escape_formula_specials(content)}$"

    return pattern.sub(repl, text)

def format_latex(md: str) -> str:
    """
    Traite les formules KaTeX dans un markdown *raw-like* :

      - ignore complètement les blocs de code :
            ```...``` ou ~~~...~~~
      - convertit \(..\) en $..$, \[..] en $$..$$
      - gère :
            $$ \n ... \n $$     (block)
            $$ ... $$           (inline display)
            $ ... $             (inline)
      - échappe les séquences d'escape foireuses dans les formules.
    """

    code_pattern = re.compile(
        r"""
        (
          ```.*?```         # bloc ```...```
        | ~~~.*?~~~         # bloc ~~~...~~~
        )
        """,
        re.VERBOSE | re.DOTALL,
    )

    parts = code_pattern.split(md)
    out_parts = []

    for part in parts:
        if not part:
            continue
        if part.startswith("```") or part.startswith("~~~"):
            # bloc de code → on ne touche à rien
            out_parts.append(part)
        else:
            # texte normal → traitement KaTeX
            out_parts.append(_escape_katex_formulas(part))

    return "".join(out_parts)

class LaTeXProcessor(Streamer):
    """Stream processor for formatting LaTeX/KaTeX formulas in markdown text.

    Escapes special characters in LaTeX formulas while preserving code blocks.
    """

    def __init__(self):
        super().__init__()
        self.token_streamer = TokenStreamer([
            # ignore processing in markdown code blocs
            (fenced('```','```',flags=re.DOTALL|re.MULTILINE), lambda m: f'{m.group()}'),
            # Mute LaTeX formulas
            (fenced(r'\$\$',r'\$\$',flags=re.DOTALL|re.MULTILINE), lambda m: f'{format_latex(m.group())}'),
            (fenced(r'\\\[',r'\\\]',flags=re.DOTALL|re.MULTILINE), lambda m: f'{format_latex(m.group())}'),
            (fenced(r'\\\(',r'\\\)',flags=re.DOTALL|re.MULTILINE), lambda m: f'{format_latex(m.group())}'),
            (r'\$[^$\n]+?\$', lambda m: f'{format_latex(m.group())}'),
        ], threaded=False)

    def stream_processor(self, stream):
        """Process stream and format LaTeX formulas."""
        return self.token_streamer.process(stream)