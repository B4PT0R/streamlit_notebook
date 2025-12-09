from .utils import utf8_safe_tokenize
import time
import re
from .stream_utils import Task, Streamer, TokenStreamer, fenced
from modict import modict
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio, _play_with_pyaudio

def silent_play(audio):
    # Sur Windows, ffplay rare, simpleaudio/pyaudio par défaut
    # Sur Linux/Mac, ffplay fréquent
    try:
        # Essaye simpleaudio
        return _play_with_simpleaudio(audio)
    except Exception:
        pass
    try:
        # Essaye pyaudio
        return _play_with_pyaudio(audio)
    except Exception:
        pass
    try:
        # Utilise ffplay en mode silencieux
        import subprocess
        import tempfile
        with tempfile.NamedTemporaryFile("w+b", suffix=".wav", delete=True) as f:
            audio.export(f.name, "wav")
            subprocess.call(
                [
                    "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", f.name
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
    except Exception:
        print("Aucun backend audio fonctionnel trouvé.")

class PlayAudio(Task):

    def __init__(self,agent,args=None,kwargs=None):
        super().__init__(args=args,kwargs=kwargs)
        self.agent=agent

    def target(self,audio):
        if audio is not None:
            if self.agent.hooks.get('audio_playback_hook'):
                self.agent.hooks.audio_playback_hook(audio)
            else:
                silent_play(audio)

class MuteTagProcessor(Streamer):
    def __init__(self,agent):
        super().__init__()
        self.agent=agent 
        self.token_streamer = TokenStreamer([
            #Intentionally muted blocs -> aggregate in buffer and pass through
            (fenced('<MUTE>','</MUTE>',flags=re.DOTALL|re.MULTILINE), lambda m: m.group()),
            # Mute markdown code blocs
            (fenced('```','```',flags=re.DOTALL|re.MULTILINE), lambda m: f'<MUTE>{m.group()}</MUTE>'),
            # Mute LaTeX formulas
            (fenced(r'\$\$',r'\$\$',flags=re.DOTALL|re.MULTILINE), lambda m: f'<MUTE>{m.group()}</MUTE>'),
            (fenced(r'\\\[',r'\\\]',flags=re.DOTALL|re.MULTILINE), lambda m: f'<MUTE>{m.group()}</MUTE>'),
            (fenced(r'\\\(',r'\\\)',flags=re.DOTALL|re.MULTILINE), lambda m: f'<MUTE>{m.group()}</MUTE>'),
            (r'\$[^$\n]+?\$', lambda m: f'<MUTE>{m.group()}</MUTE>'),
            # Mute links
            (r'https?://\S+', lambda m: f'<MUTE>{m.group()}</MUTE>'),
        ], threaded=False)
        
    def stream_processor(self, stream):
        return self.token_streamer.process(stream)

class MuteAnalyzer(Streamer):

    def __init__(self,agent):
        super().__init__()
        self.agent=agent

    """Splits token stream into muted and non-muted parts"""
    def stream_processor(self, stream):       
        for token in stream:
            if token.startswith('<MUTE>') and token.endswith('</MUTE>'):
                yield ('mute', token[6:-7])  # Strip <MUTE>...</MUTE> tags
            else:
                yield ('speak',token)

class LineAgregator(Streamer):

    def __init__(self,agent):
        super().__init__()
        self.agent=agent

    def stream_processor(self,stream):
        lines=""
        token_count=0
        last_mode=None
        for mode, token in stream:

            if mode!=last_mode:
                if lines and last_mode is not None:
                    yield (last_mode,lines)
                lines=""
                token_count=0
                last_mode=mode

            token_count+=1
            while '\n' in token: #in case a token contains several occurences of '\n'
                parts=token.split('\n')
                lines+=parts[0]+'\n'
                if token_count>50:
                    yield (last_mode,lines)
                    lines=""
                    token_count=0
                token='\n'.join(parts[1:])
            else:
                lines+=token
        if lines and last_mode is not None:
            yield (last_mode,lines)

class LineToAudio(Streamer):

    def __init__(self,agent):
        super().__init__()
        self.agent=agent
    
    def text_to_audio(self,text):
        # Create MP3 audio
        
        if text.strip():

            params=modict(
                model=self.agent.config.get('voice_model','gpt-4o-mini-tts'),
                voice=self.agent.config.get('voice','nova'),
                instructions=self.agent.config.get('voice_instructions','You speak with a friendly and casual tone.'),
                input=text
            )

            audio = self.agent.ai.text_to_audio(**params)

            return audio
        else:
            return None

    def stream_processor(self,stream):
        for mode,line in stream:
            if not line:
                continue

            if mode=='mute':
                audio=None
            else:
                audio=self.text_to_audio(line)

            yield (line,audio)

class AudioPlayer(Streamer):

    def __init__(self,agent):
        super().__init__()
        self.agent=agent

    def stream_processor(self,stream):
        for line,audio in stream:
            tokenized=utf8_safe_tokenize(line)
            if audio is not None:
                sleep_time_per_token = 0.95*(audio.duration_seconds / len(tokenized))  # Durée ajustée par token
                task=PlayAudio(self.agent,args=(audio,))
                task.start()
                for token in tokenized:
                    yield token
                    time.sleep(sleep_time_per_token)
                task.join()
            else:
                for token in tokenized:
                    yield token
                    time.sleep(0.02)

class Throttler(Streamer):

    def __init__(self,agent):
        super().__init__()
        self.agent=agent

    def stream_processor(self,stream):
        buffer=''
        buffer_size=self.agent.config.get('voice_buffer_size',3) # Number of tokens to buffer before yielding the result
        for i,token in enumerate(stream):
            buffer+=token
            if i%buffer_size==0:
                yield buffer
                buffer=''
        if buffer:
            yield buffer
            


class VoiceProcessor(Streamer):
    """
    Class handling TTS.
    Uses the speak method as entry point.
    Takes a token stream as input.
    Speaks the stream as it goes.
    Returns a token stream synchronized with speech.
    """

    def __init__(self,agent):
        super().__init__()
        self.agent=agent
        self.mute_tag_processor=MuteTagProcessor(self.agent)
        self.line_splitter=LineAgregator(self.agent)
        self.line_to_audio=LineToAudio(self.agent)
        self.speech_processor=AudioPlayer(self.agent)
        self.mute_analyzer=MuteAnalyzer(self.agent)
        self.throttler=Throttler(self.agent)

    def __call__(self,stream):
        if self.agent.config.get('voice_enabled',False):
            return self.process(stream)
        else:
            return stream
        
    def stream_processor(self, stream):
        tagged_stream = self.mute_tag_processor.process(stream)
        analyzed_stream= self.mute_analyzer.process(tagged_stream)
        marked_lines = self.line_splitter.process(analyzed_stream)
        lines_with_playback = self.line_to_audio.process(marked_lines)
        synced_stream=self.speech_processor.process(lines_with_playback)
        throttled_stream=self.throttler.process(synced_stream)
        return throttled_stream            

