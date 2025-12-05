import os
import tiktoken
import re
from datetime import datetime
from textwrap import dedent
import random, string
import json
import regex
from threading import Thread as ThreadBase
import sys

# Try to import full get_text with all document processing capabilities
# Fall back to simpler version if dependencies are missing
try:
    from .get_text import get_text
except ImportError:
    from .simpler_get_text import get_text

def set_root_path(file=None):
    file=file or __file__
    os.environ['ROOT_PACKAGE_FOLDER']=os.path.dirname(os.path.abspath(file))

def root_join(*args):
    return os.path.join(os.getenv('ROOT_PACKAGE_FOLDER'),*args)

def text_content(file):
    if os.path.isfile(file):
        with open(file,encoding="utf-8") as f:
            return f.read()
    else:
        return None
    
def add_line_numbers(text: str) -> str:
    lines = text.splitlines()
    n = len(lines)
    width = len(str(n))
    
    lines_num = [f"{i:0{width}d}|{line}" 
                  for i, line in enumerate(lines, start=1)]
    return "\n".join(lines_num)
    
def short_id(length=8):
    return "".join(random.choices(string.ascii_letters,k=length))

def session_id():
    """Generate a unique session ID with timestamp"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

tokenizer = tiktoken.get_encoding("cl100k_base")

def tokenize(string):
    int_tokens = tokenizer.encode(string)
    str_tokens = [tokenizer.decode([int_token]) for int_token in int_tokens]
    return str_tokens

def utf8_safe_tokenize(s):
    return regex.findall(r'\X', s)

def token_count(string):
    return len(tokenizer.encode(string))

def sort(messages):
    return sorted(messages, key=lambda msg: msg.timestamp)

def truncate(string, max_tokens=2000, start_line=1):
    """
    Truncate a string to a maximum number of tokens using line-based chunking.

    Args:
        string: The string to truncate
        max_tokens: Maximum number of tokens to keep
        start_line: The line number of the first line in the string (1-indexed).
                   Used for skipping content and tracking line numbers in truncation messages.

    Returns:
        Truncated string with indication of removed content
    """
    # Quick check - if already under limit, return as-is
    tokens = tokenize(string)
    if len(tokens) <= max_tokens:
        return string

    # line-based truncation
    lines = string.splitlines(keepends=True)
    total_lines = len(lines)

    # Skip to start_line if needed
    if start_line > 1:
        if start_line > len(lines):
            return ""
        lines = lines[start_line - 1:]

    # Calculate the actual last line number after skipping
    remaining_lines = len(lines)

    # Assemble lines up to max_tokens
    result_lines = []
    current_tokens = 0

    for line in lines:
        line_tokens = token_count(line)
        if current_tokens + line_tokens <= max_tokens:
            result_lines.append(line)
            current_tokens += line_tokens
        else:
            break

    if result_lines:
        result = ''.join(result_lines)
        num_kept = len(result_lines)

        # Only show truncation message if we didn't include all lines
        if num_kept < remaining_lines:
            first_truncated = start_line + num_kept
            last_line = start_line + remaining_lines - 1

            if not result.endswith('\n'):
                result += '\n'
            result += f"\n...\n\n[Lines {first_truncated}-{last_line} truncated]\n"

        return result
    else:
        return f"[Lines {start_line}-{start_line + remaining_lines - 1} truncated - content exceeds token limit]\n"

def pack_msgs(messages):
    text = ''
    for message in messages:
        text += message.name + ':\n'
        text += message.content.strip() + '\n\n'
    return text

def msg_token_count(msg):
    count=0
    if msg.type=='image':
        if isinstance(msg.content,list):
            for item in msg.content:
                if item.get('type')=='image_url':
                    count+=1000
                elif item.get('type')=='text':
                    count+=token_count(str(item.get('text') or ''))
        else:
            count+=token_count(str(msg.get('content') or ''))
    else:
        count+=token_count(str(msg.get('content') or ''))

    for tool_call in msg.get('tool_calls') or []:
        count+=token_count(json.dumps(tool_call.function.arguments))
    return count

def total_tokens(messages):
    return sum(msg_token_count(msg) for msg in messages)

def extract_python(text, pattern=None):
    pattern = pattern or r'```run_python(.*?)```'
    iterator = re.finditer(pattern, text, re.DOTALL)
    return [match.group(1) for match in iterator]

def format(string, context=None):
    # Si aucun contexte n'est fourni, utiliser un dictionnaire vide
    if context is None:
        context = {}
    # Trouver les expressions entre <<...>>
    def replace_expr(match):
        expr = match.group(1)
        try:
            # Évaluer l'expression dans le contexte donné et la convertir en chaîne
            return str(eval(expr, context))
        except Exception as e:
            # print(f"could not evaluate expr: {expr}\n Exception:\n {str(e)}")
            # En cas d'erreur, retourner l'expression non évaluée
            return '<<' + expr + '>>'
    # Remplacer chaque expression par son évaluation
    return re.sub(r'<<(.*?)>>', replace_expr, string)

def timestamp(digits=3):
    base = datetime.now().strftime("%Y%m%dT%H%M%S.%f")
    if digits == 0:
        return base[:15]  # Jusqu'à la seconde uniquement
    return base[:15 + 1 + digits]

class NoContext:
    """
    A context manager that does nothing, useful when no context manager is required to display a message.
    """
    def __init__(self,*args,**kwargs):
        pass
    def __enter__(self,*args,**kwargs):
        pass
    def __exit__(self,*args,**kwargs):
        pass

def guess_extension_from_bytes(data):
    """
    Guess file extension from byte content using filetype library.
    Returns None if unable to determine the file type.

    Args:
        data: bytes or BytesIO object containing file data

    Returns:
        str: File extension with leading dot (e.g., '.png') or None if unable to determine
    """
    import filetype
    from io import BytesIO

    # Ensure we have bytes
    if isinstance(data, BytesIO):
        data = data.getvalue()
    elif hasattr(data, 'read'):
        data = data.read()

    if not data or len(data) == 0:
        return None

    kind = filetype.guess(data)
    if kind is not None:
        return f'.{kind.extension}'

    return None

class Logger:

    def __init__(self,file=None):
        self.file=file or root_join('logs',"log.txt")
        open(self.file,'w').close()

    def log(self,message):
        with open(self.file,'a',encoding="utf-8") as f:
            f.write(str(message)+'\n')

    def log_to_file(self,content,file=None):
        file = file or self.file
        with open(file,'w',encoding="utf-8") as f:
            f.write(str(content)+'\n')

def read_document_content(source, start_at_line=1, max_tokens=8000):
    """
    Read and extract text content from various document formats.

    Args:
        source: Document source - either a local file path or URL (http/https)
        start_at_line: Line number to start reading from (1-indexed)
        max_tokens: Maximum tokens for truncation (0 to disable)

    Returns:
        Extracted text content, possibly truncated
    """

    text=get_text(source)

    # Apply truncation - truncate function handles smart chunking internally
    if max_tokens > 0:
        text = truncate(text, max_tokens=max_tokens, start_line=start_at_line)

    return text

def is_running_in_streamlit_runtime():
    try:
        import streamlit.runtime.scriptrunner
        return True
    except Exception:
        return False

def Thread(*args,**kwargs):
    thread=ThreadBase(*args,**kwargs)
    if is_running_in_streamlit_runtime():
        from streamlit.runtime.scriptrunner import get_script_run_ctx,add_script_run_ctx
        ctx=get_script_run_ctx()
        add_script_run_ctx(thread,ctx)
    return thread

