from queue import Queue
from inspect import isgenerator
from threading import ThreadError
import time
import regex  # Third-party regex module
import re
from typing import Generator, List, Iterable, Callable, Tuple, Union
from .utils import tokenize, Thread
from textwrap import dedent
import json

def log(*data):
    if False:
        print(*data)
        input()

class Task:

    def __init__(self,target=None,args=None,kwargs=None):
        self.target_task=target or self.target
        self.args=args if args is not None else ()
        self.kwargs=kwargs if kwargs is not None else {}
        self.thread=None
        
    def target(self,*args,**kwargs):
        pass

    def start(self):
        self.thread=Thread(target=self.target_task,args=self.args,kwargs=self.kwargs)
        self.thread.start()

    def join(self):
        self.thread.join()

class Tee:

    def __init__(self):
        self.queues={}
        self.thread=None

    def target(self,stream):
        for chunk in stream:
            for k in self.queues:
                self.queues[k].put(chunk)
            time.sleep(0.0005)
        for k in self.queues:
            self.queues[k].put("#END#")
        
    def tee(self,stream, n=2):
        self.queues={k:Queue() for k in range(n)}
        self.thread=Thread(target=self.target, args=(stream,),kwargs=dict(n=n))
        self.thread.start()
        readers={}
        for k in self.queues:
            def reader():
                while not (processed_chunk:=self.queues[k].get())=="#END#":
                    yield processed_chunk
            readers[k]=reader()
        return tuple(readers.values())
    
class Splitter:

    def __init__(self,condition=None):
        self.queue_true=None
        self.queue_false=None
        self.condition=condition or self.split_condition
        self.thread=None

    def split_condition(self,chunk):
        return True

    def target(self,stream):
        for chunk in stream:
            if self.condition(chunk):
                self.queue_true.put(chunk)
            else:
                self.queue_false.put(chunk)
        self.queue_true.put("#END#")
        self.queue_false.put("#END#")
        
    def split(self, stream):
        self.queue_true=Queue()
        self.queue_false=Queue()
        self.thread=Thread(target=self.target, args=(stream,))
        self.thread.start()
        def reader_true():
            while not (chunk:=self.queue_true.get())=="#END#":
                yield chunk
        def reader_false():
            while not (chunk:=self.queue_false.get())=="#END#":
                yield chunk
        return reader_true(),reader_false()


    
class Streamer:

    def __init__(self,stream_processor=None,threaded=True):
        self.queue=None
        self.threaded=threaded
        self.process_stream=stream_processor or self.stream_processor

    def stream_processor(self,stream):
        """
        Default stream processor : Just yields the stream, does nothing else
        Can be overriden in subclasses or bypassed by providing a stream_processor to the instance
        """
        return stream

    def target(self,stream):
        for processed_chunk in self.process_stream(stream):
            time.sleep(0.0005)
            self.queue.put(processed_chunk)
        self.queue.put("#END#")
        
    def process(self,stream):
        if self.threaded:
            self.queue=Queue()
            self.thread=Thread(target=self.target, args=(stream,))
            self.thread.daemon=True
            self.thread.start()
            def reader():
                while not (processed_chunk:=self.queue.get())=="#END#":
                    yield processed_chunk
            return reader()
        else:
            return self.process_stream(stream)
        
    def __call__(self, stream):
        return self.process(stream)
        

class StreamLogger(Streamer):

    def __init__(self,threaded=True,file=None):
        super().__init__(threaded=threaded)
        self.file=file

    def stream_processor(self, stream):
        output=""
        for token in stream:
            if token:
                output += token
                yield token
        if self.file is not None:
            import os
            if not os.path.isfile(self.file):
                open(self.file,'w').close()
            with open(self.file,'a') as f:
                f.write(output)
        
def fenced(start: Union[str,regex.Pattern,re.Pattern], end: Union[str,regex.Pattern,re.Pattern], flags=0) -> regex.Pattern:
    """
    Generates a regex pattern that matches text enclosed between a start and an end delimiter,
    The inner part is captured as the 'content' group (default).
    There can be other captured groups defined in the start and end patterns.
    The end delimiter can include backreferences to captured groups from the opening fence into placeholders in the closing fence.

    The closing fence pattern may include placeholders in the form of "#1#" for the first captured group,
    "#2#" for the second, or "#name#" for a named capturing group; these will be replaced by the appropriate
    backreference. This mechanism is completely generic and does not enforce any specific delimiter shapes.

    Example:
        # Using a numeric placeholder:
        pattern = fenced(r"START (\w+)", r"END #1#", flags=regex.DOTALL)
        text = "START content END content"
        match = pattern.match(text)
        if match:
            print(match.group())

        # Using a named capturing group:
        pattern = fenced(r"BEGIN (?P<tag>\w+)", r"FIN #tag#", flags=regex.DOTALL)
        text = "BEGIN example FIN example"
        match = pattern.match(text)
        if match:
            print(match.group())

    :param start: Opening delimiter (str or regex.Pattern). May contain capturing groups.
    :param end: Closing delimiter (str or regex.Pattern) which may include placeholders (e.g., "#1#", "#name#").
    :param flags: Regex flags to modify behavior (e.g., regex.DOTALL, regex.MULTILINE).
    :return: A compiled regex pattern.
    """
    def prepare_pattern(pattern):
        if isinstance(pattern, (regex.Pattern,re.Pattern)):
            return pattern.pattern
        if isinstance(pattern, str):
            return pattern
        raise ValueError("`start` and `end` must be either a string or a regex Pattern object")
    
    start_regex = prepare_pattern(start)   
    end_regex   = prepare_pattern(end)
    
    # Replace placeholders in end pattern with regex backrefs
    def replace_placeholder(match):
        key = match.group(1)
        if key.isdigit():
            return rf"\{key}"
        else:
            return rf"(?P={key})"
    end_regex = regex.sub(r"#(\w+)#", replace_placeholder, end_regex)
    
    # Named content group
    inner = rf'(?P<content>(?:(?!{end_regex})[\s\S])*)'
    
    full_pattern = rf'{start_regex}{inner}(?:{end_regex}|$)'
    return regex.compile(full_pattern, flags)

def is_compiled_pattern(pattern):
    if isinstance(pattern, (re.Pattern,regex.Pattern)):
        return True
    elif isinstance(pattern,str):
        return False
    else:
        raise ValueError(f"Expected either a string, re.Pattern or regex.Pattern object. got {type(pattern)}")
    
def is_re_pattern(pattern):
    return isinstance(pattern,re.Pattern)

class TokenStreamer(Streamer):

    def __init__(self, patterns, threaded=True):
        """
        :param patterns: List of tuples (pattern, processing_func).
                         `pattern` peut être une string, un re.Pattern ou un regex.Pattern.
                         `processing_func` doit être de la forme:
                             lambda match: output_str
        """
        super().__init__(threaded=threaded)
        self.compiled_patterns = []
        for pattern, func in patterns:
            if is_compiled_pattern(pattern):
                if is_re_pattern(pattern):
                    # recompile avec regex pour autoriser les partial matches
                    self.compiled_patterns.append(
                        (regex.compile(pattern.pattern, flags=pattern.flags), func)
                    )
                else:
                    self.compiled_patterns.append((pattern, func))
            else:
                self.compiled_patterns.append((regex.compile(pattern), func))

    def update_candidates(self, buffer, candidates):
        """
        Pour chaque pattern, on tente de matcher le buffer en mode partial.
        Si le match est trouvé, on le stocke dans candidates.

        candidates: dict[index_pattern] = (match_obj, is_complete: bool)
        """
        if buffer:
            for i, (pattern, _) in enumerate(self.compiled_patterns):
                match = regex.match(pattern, buffer, partial=True)
                if match:
                    # match_obj = match
                    # Si le match s'étend jusqu'à la fin du buffer, on ne peut pas conclure.
                    if match.span()[1] == len(buffer):
                        candidates[i] = (match, False)
                    else:
                        # Des caractères en plus après le match → pattern terminé.
                        candidates[i] = (match, True)
                else:
                    candidates.pop(i, None)
        return candidates

    def compute_output(self, buffer, candidates):
        """
        Si un unique candidat est présent et marqué comme complet, on le traite et on le transforme.
        On ne valide le candidat que s'il ne couvre PAS exactement tout le buffer
        (évite de traiter un match susceptible d'être prolongé).
        """
        if len(candidates) == 1:
            key = list(candidates.keys())[0]
            match, is_complete = candidates[key]
            full = match.group(0)

            # Ne traiter que si le match est complet ET que le buffer contient plus que le candidat
            if is_complete and len(full) < len(buffer):
                _, func = self.compiled_patterns[key]
                new_buffer = buffer[len(full):]
                del candidates[key]
                # On passe directement le match à la fonction de traitement
                return func(match), new_buffer, candidates
            else:
                return None, buffer, candidates

        if len(candidates) == 0:
            if buffer:
                # Pas de pattern détecté, on avance d'un caractère.
                char = buffer[0]
                new_buffer = buffer[1:]
                return char, new_buffer, candidates
            else:
                return None, buffer, candidates
        else:
            return None, buffer, candidates

    def yield_greediest(self, buffer):
        """
        Lors du vidage du buffer, on tente de trouver parmi tous les patterns celui qui correspond le mieux
        (le plus long match commençant au début) et on le traite.
        """
        matching = []
        for pattern, func in self.compiled_patterns:
            match = regex.match(pattern, buffer)
            if match and match.span()[0] == 0:
                matching.append((func, match))

        if matching:
            # On choisit le match le plus long
            func, match = sorted(matching, key=lambda x: len(x[1].group(0)), reverse=True)[0]
            full = match.group(0)
            processed = func(match)
            new_buffer = buffer[len(full):]
            return processed, new_buffer
        else:
            return None, buffer

    def stream_processor(self, stream):
        """
        Accumule les tokens dans un buffer et tente de détecter, dès que possible, des patterns à transformer.
        """
        buffer = ''
        candidates = {}
        
        for token in stream:
            if not token:
                continue

            buffer += token
            keep_on_checking = True
            
            while keep_on_checking:
                candidates = self.update_candidates(buffer, candidates)
                output, buffer, candidates = self.compute_output(buffer, candidates)
                if output is not None:
                    yield output
                else:
                    keep_on_checking = False

        # Vidage du buffer une fois le flux terminé
        while buffer:
            processed, buffer = self.yield_greediest(buffer)
            if processed:
                yield processed
            else:
                yield buffer[0]
                buffer = buffer[1:]

class Extractor(Streamer):
    
    def __init__(self, pattern, ignore=None, threaded=True):
        super().__init__(threaded=threaded)
        ignore=ignore or []
        self.token_streamer = TokenStreamer([
            # ignore processing for patterns in ignore, we just keep them in the output
            *[(ignored,(lambda m:m.group(0))) for ignored in ignore],
            (pattern, self.process_match)
        ], threaded=False)
        self.matchs=[]
        
    def stream_processor(self, stream):
        self.matchs=[]
        return self.token_streamer(stream)
    
    def process_match(self,match):
        self.matchs.append(match)
        return ''

class XMLExtractor(Extractor):
    # Attributs XML : string, int, float, bool, null, json object/list
    ATTR_RE = regex.compile(
        r"""
        (?P<name>[A-Za-z_][\w:.-]*)   # nom
        \s*=\s*
        (
          (?P<quote>["'])(?P<qvalue>.*?)(?P=quote)   # valeur "quoted"
          |
          (?P<uvalue>[^\s>]+)                         # valeur non-quotée
        )
        """,
        regex.VERBOSE | regex.DOTALL,
    )

    def __init__(self,threaded=True):
        pattern = fenced(
            r"<(?P<tool>[A-Za-z_][\w\-.]*)"
            r"(?P<attrs>[^>]*)>",
            r"</#tool#>",
            flags=regex.DOTALL,
        )
        ignore=[fenced('```','```',flags=re.DOTALL|re.MULTILINE)]
        super().__init__(pattern, ignore=ignore, threaded=threaded)

    @classmethod
    def parse_attrs(cls, attrs_src: str) -> dict:
        attrs_src = attrs_src or ""
        result = {}

        for m in cls.ATTR_RE.finditer(attrs_src):
            name = m.group("name")
            raw = m.group("qvalue") or m.group("uvalue") or ""

            try:
                # JSON-compatible values: numbers, booleans, null, dicts, lists…
                value = json.loads(raw)
            except Exception:
                # else keep raw string
                value = raw

            result[name] = value

        return result

    def process_match(self, match):
        tool = match.group("tool")
        attrs_src = match.group("attrs") or ""
        content = match.group("content") or ""

        args = self.parse_attrs(attrs_src)
        args["content"] = content.strip('\n')      # 🔥 INTÉGRATION DIRECTE ICI 🔥

        self.matchs.append({
            "name": tool,
            "args": args,        # dict final prêt pour un tool call
            "match": match,
        })
        return f'```Called {tool!r} tool via XML (tool call details accessible in message.tool_calls)```'  # on retire le bloc XML du texte visible

class MarkdownBlockExtractor(Extractor):
    """
    En fait maintenant : extracteur de blocs markdown tool.

    Forme reconnue :

        ```tool_name(foo=1, bar="x", debug=true)
        ...content...
        ```

    -> match :
       - tool   : "tool_name"
       - args   : dict typé (int, float, bool, None, objets/lists JSON...)
       - content: texte intérieur (multi-ligne)
    """   

    KWARG_RE = regex.compile(
        r"""
        (?P<name>[A-Za-z_]\w*)
        \s*=\s*
        (
          (?P<quote>["'])(?P<qvalue>.*?)(?P=quote)
          |
          (?P<uvalue>[^,\s)]+)
        )
        (?:\s*,\s*|$)
        """,
        regex.VERBOSE | regex.DOTALL,
    )

    def __init__(self, ignore=None, threaded=True):
        # Exactly 3 backticks: (?<!`)```(?!`)
        start = (
            r"(?<!`)```(?!`)"                           # EXACTLY 3 backticks
            r"(?P<tool>[A-Za-z_][\w\-.]*)"             # tool name
            r"(?:\((?P<raw_args>[^\n)]*)\))?"          # optional (...args...)
            r"[^\n]*\n"                                # rest of the line + newline
        )

        end = r"(?<!`)```(?!`)[ \t]*"                   # closing fence (exactly 3)

        pattern = fenced(start, end, flags=regex.DOTALL)
        super().__init__(pattern, ignore=ignore, threaded=threaded)

    @classmethod
    def parse_kwargs(cls, raw_args: str) -> dict:
        raw_args = (raw_args or "").strip()
        if not raw_args:
            return {}

        result = {}
        for m in cls.KWARG_RE.finditer(raw_args):
            name = m.group("name")
            raw_val = m.group("qvalue") or m.group("uvalue") or ""
            try:
                value = json.loads(raw_val)
            except Exception:
                value = raw_val
            result[name] = value

        return result

    def process_match(self, match):
        tool = match.group("tool")
        raw_args = match.group("raw_args") or ""   # <= si pas de (), ça devient ""
        content = match.group("content") or ""

        args = self.parse_kwargs(raw_args)
        args["content"] = content

        self.matchs.append({
            "name": tool,
            "args": args,
            "match": match,
        })

        # On renvoie le bloc tel quel
        return match.group()

class MappingStreamSplitter:

    """converts a stream of Mappings into a dict of streams, one for each key of the Mapping data"""

    def __init__(self, defaults=None, threaded=False):
        self.threaded=threaded
        self.readers=dict()
        self.queues=dict()
        self.defaults=defaults or {}

    def maybe_init_readers(self, data):
        for key in data.keys():
            if key not in self.readers:
                self.queues[key]=Queue()
                def reader(key=key):
                    while not (value:=self.queues[key].get())=="#END#":
                        yield value
                self.readers[key]=reader()

    def process(self,stream):
        self.queues=dict()
        if self.defaults:
            self.maybe_init_readers(self.defaults)
        for data in stream:
            self.maybe_init_readers(data)
            for key, value in data.items():
                self.queues[key].put(value)
            for key in set(self.defaults.keys())-set(data.keys()):
                self.queues[key].put(self.defaults[key])
            if self.threaded:
                time.sleep(0.0005)
        for key in self.queues:
            self.queues[key].put("#END#")

    def split(self, stream):
        if self.threaded:
            thread=Thread(target=self.process, args=(stream,))
            thread.start()
            time.sleep(0.01) # let (at least) the default readers be initialized
        else:
            self.process(stream)
        return self.readers 
        #warning! in threaded mode, readers will be added dynamically as new keys are encountered
        #it's better suited for streams with a predictable set of keys
    
    def __call__(self, stream):
        return self.split(stream)
    
class MappingStreamGatherer:

    """
    Does it backwards, it takes a dict of streams and returns a stream of Mappings of the chosen type (default, dicts)
    """

    def __init__(self, defaults=None, type=None, threaded=False):
        self.type=type or dict
        self.defaults=defaults or {}
        self.threaded=threaded
        self.queue=None

    def process(self, streams:dict):
        streams=streams.copy()
        while True:
            data={}
            for key, stream in list(streams.items()): #list because new readers may appear or be deleted as we loop
                try:
                    data[key]=next(stream)
                except StopIteration:
                    # the stream is consumed
                    del streams[key]
            if data:
                for key, default in self.defaults.items():
                    data.setdefault(key, default)
                self.queue.put(self.type(data))
            if not streams:
                break
        self.queue.put("#END#")

    def gather(self, streams:dict):
        self.queue=Queue()
        if self.threaded:
            Thread(target=self.process, args=(streams,)).start()
        else:
            self.process(streams)
        
        def stream():
            while not (mapping:=self.queue.get())=="#END#":
                yield mapping
        
        return stream()
    
    def __call__(self, streams:dict):
        return self.gather(streams)

class MappingStreamProcessor(Streamer):

    """
    Allows to plug specific processors (Streamers) to specific keys of a stream of mappings
    """
    
    def __init__(self, defaults=None, processors=None, type=None, threaded=False):
        super().__init__(threaded=threaded)
        self.type=type if type is not None else dict
        self.defaults=defaults if defaults is not None else {}
        self.processors=processors if processors is not None else {}
        self.splitter=MappingStreamSplitter(defaults=self.defaults, threaded=True)
        self.gatherer=MappingStreamGatherer(defaults=self.defaults, type=self.type, threaded=True)

    def stream_processor(self, stream):
        if not self.processors:
            return stream
        streams=self.splitter(stream)
        processed_streams=dict()
        for key, stream in streams.items():
            if key in self.processors:
                if isinstance(self.processors[key],list):
                    processors=self.processors[key]
                    for processor in reversed(processors):
                        stream=processor(stream)
                elif callable(self.processors[key]):
                    stream=self.processors[key](stream)
            processed_streams[key]=stream
        return self.gatherer(processed_streams)
    
        
        
        
