from queue import Queue
from inspect import isgenerator
import time
import regex  # Third-party regex module
import re
from typing import Generator, List, Iterable, Callable, Tuple, Union
from .utils import tokenize, Thread
from textwrap import dedent

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
        for k in self.queues:
            self.queues[k].put("#END#")
        
    def tee(self, stream, n=2):
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
    while allowing mapping of captured groups from the opening fence into placeholders in the closing fence.

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
            return pattern.pattern  # Use the raw pattern string if already compiled.
        if isinstance(pattern, str):
            return pattern  # Assume the user provided a valid regex.
        raise ValueError("`start` and `end` must be either a string or a regex Pattern object")
    
    start_regex = prepare_pattern(start)   
    end_regex = prepare_pattern(end)
    
    # Replace placeholders in the end pattern with the corresponding backreferences.
    def replace_placeholder(match):
        key = match.group(1)
        if key.isdigit():
            return rf"\{key}"
        else:
            return rf"(?P={key})"
    end_regex = regex.sub(r"#(\w+)#", replace_placeholder, end_regex)
    
    # Inner part: matches greedily until the closing fence (without consuming it).
    inner = rf'((?:(?!{end_regex})[\s\S])*)'
    
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
        Initialise le TokenStreamer.
        :param patterns: List of tuples (pattern, processing_func). `pattern` can be either a raw string, a re.Pattern or a regex.Pattern object
        :param threaded: boolean indicating if the processing happens in a separate thread.
        """
        super().__init__(threaded=threaded)
        self.compiled_patterns = []
        for pattern, func in patterns:
            if is_compiled_pattern(pattern):
                if is_re_pattern(pattern):
                    # recompile with regex to allow partial matches
                    self.compiled_patterns.append((regex.compile(pattern.pattern,flags=pattern.flags),func))
                else:
                    self.compiled_patterns.append((pattern,func))
            else:
                self.compiled_patterns.append((regex.compile(pattern), func))

    def update_candidates(self, buffer, candidates):
        """
        Pour chaque pattern, on tente de matcher le buffer en mode partial.
        Si le match est trouvé, on le stocke dans candidates.
        On considère le match comme potentiellement complet uniquement si le match ne couvre PAS
        l'intégralité du buffer. Sinon, on le laisse en attente (incomplet).
        """
        if buffer:
            for i, (pattern, _) in enumerate(self.compiled_patterns):
                match = regex.match(pattern, buffer, partial=True)
                if match:
                    # Si le match s'étend jusqu'à la fin du buffer, on ne peut pas conclure. un token additionel pourrait venir étendre le pattern.
                    if match.span()[1] == len(buffer):
                        # Même si match.partial est False, si on n'a pas de "dépassement", on attend.
                        candidates[i] = (match.group(), False)
                    else:
                        # Si le match se termine avant la fin du buffer, c'est que des caractères supplémentaires
                        # indiquent que le pattern est terminé.
                        candidates[i] = (match.group(), True)
                else:
                    candidates.pop(i, None)
        # print(f"buffer:{buffer!r} ; candidates:{candidates}")
        return candidates

    def compute_output(self, buffer, candidates):
        """
        Si un unique candidat est présent et marqué comme complet, on le traite et on le transforme.
        IMPORTANT : on ne valide le candidat que s'il ne couvre PAS exactement tout le buffer.
        Cela garantit qu'on ne traite pas un match susceptible d'être prolongé.
        """
        if len(candidates) == 1:
            key = list(candidates.keys())[0]
            candidate, is_complete = candidates[key]
            # Ne traiter que si le match est complet ET que le buffer contient plus que le candidat
            if is_complete and len(candidate) < len(buffer):
                _, func = self.compiled_patterns[key]
                new_buffer = buffer[len(candidate):]
                del candidates[key]
                return func(candidate), new_buffer, candidates
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
            match = regex.match(pattern,buffer)
            if match and match.span()[0] == 0:
                matching.append((func, match.group()))
        if matching:
            func, string = sorted(matching, key=lambda x: len(x[1]), reverse=True)[0]
            processed = func(string)
            new_buffer = buffer[len(string):]
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