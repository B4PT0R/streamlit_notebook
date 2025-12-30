from .utils import utf8_safe_tokenize
import time
import re
from .stream_utils import Task, Streamer, TokenStreamer, fenced
from modict import modict
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio, _play_with_pyaudio

def silent_play(audio):
    """Play audio using the best available backend without console output.

    Tries backends in order: simpleaudio, pyaudio, ffplay.

    Args:
        audio: AudioSegment object to play.
    """
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
    """Task for playing audio asynchronously.

    Args:
        agent: The agent instance.
        args: Positional arguments for the task.
        kwargs: Keyword arguments for the task.
    """

    def __init__(self,agent,args=None,kwargs=None):
        super().__init__(args=args,kwargs=kwargs)
        self.agent=agent

    def target(self,audio):
        """Play audio using hook if available, otherwise use silent_play.

        Args:
            audio: AudioSegment to play.
        """
        if audio is not None:
            if self.agent.hooks.get('audio_playback_hook'):
                self.agent.hooks.audio_playback_hook(audio)
            else:
                silent_play(audio)

class MuteTagProcessor(Streamer):
    """Stream processor that wraps code blocks, LaTeX formulas, and links in MUTE tags.

    These tagged sections will be skipped during text-to-speech conversion.

    Args:
        agent: The agent instance.
    """

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
        """Process stream and add MUTE tags around code/formulas/links."""
        return self.token_streamer.process(stream)

class MuteAnalyzer(Streamer):
    """Splits token stream into muted and non-muted parts.

    Args:
        agent: The agent instance.
    """

    def __init__(self,agent):
        super().__init__()
        self.agent=agent

    def stream_processor(self, stream):
        """Split stream into tuples of (mode, text) where mode is 'mute' or 'speak'."""
        for token in stream:
            if token.startswith('<MUTE>') and token.endswith('</MUTE>'):
                yield ('mute', token[6:-7])  # Strip <MUTE>...</MUTE> tags
            else:
                yield ('speak',token)

class LineAgregator(Streamer):
    """Aggregates tokens into lines for voice processing.

    Buffers tokens until newline characters are encountered or token count
    exceeds threshold, then yields complete lines with their mode (mute/speak).

    Args:
        agent: The agent instance.
    """

    def __init__(self,agent):
        super().__init__()
        self.agent=agent

    def stream_processor(self,stream):
        """Aggregate tokens into lines based on newlines and token count.

        Args:
            stream: Input stream of (mode, token) tuples.

        Yields:
            Tuples of (mode, line_text) for each aggregated line.
        """
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
    """Converts text lines to audio segments using text-to-speech.

    Args:
        agent: The agent instance with AI client for TTS.
    """

    def __init__(self,agent):
        super().__init__()
        self.agent=agent

    def text_to_audio(self,text):
        """Convert text to audio using configured TTS model.

        Args:
            text: Text string to convert to speech.

        Returns:
            AudioSegment object or None if text is empty.
        """
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
        """Process stream of lines, converting non-muted text to audio.

        Args:
            stream: Stream of (mode, line) tuples.

        Yields:
            Tuples of (line, audio) where audio is AudioSegment or None for muted lines.
        """
        for mode,line in stream:
            if not line:
                continue

            if mode=='mute':
                audio=None
            else:
                audio=self.text_to_audio(line)

            yield (line,audio)

class AudioPlayer(Streamer):
    """Plays audio while streaming tokens at synchronized pace.

    Plays audio segments in background while yielding tokens at a rate
    synchronized with the audio playback duration.

    Args:
        agent: The agent instance.
    """

    def __init__(self,agent):
        super().__init__()
        self.agent=agent

    def stream_processor(self,stream):
        """Play audio and yield tokens synchronized with playback.

        Args:
            stream: Stream of (line, audio) tuples.

        Yields:
            Individual tokens with timing synchronized to audio playback.
        """
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
    """Buffers and batches tokens to control output rate.

    Accumulates tokens in a buffer and yields them in batches to prevent
    overwhelming downstream consumers.

    Args:
        agent: The agent instance with buffer size configuration.
    """

    def __init__(self,agent):
        super().__init__()
        self.agent=agent

    def stream_processor(self,stream):
        """Buffer and batch tokens before yielding.

        Args:
            stream: Input token stream.

        Yields:
            Batched token strings.
        """
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
    """Orchestrates text-to-speech processing for token streams.

    Coordinates multiple processing stages:
    1. Tags code blocks, formulas, and links as muted
    2. Analyzes and splits into muted/spoken sections
    3. Aggregates tokens into lines
    4. Converts spoken lines to audio
    5. Plays audio synchronized with token output
    6. Throttles output for controlled streaming

    Args:
        agent: The agent instance with voice configuration.
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
        """Process stream with voice if enabled, otherwise pass through.

        Args:
            stream: Input token stream.

        Returns:
            Processed token stream (with or without voice).
        """
        if self.agent.config.get('voice_enabled',False):
            return self.process(stream)
        else:
            return stream

    def stream_processor(self, stream):
        """Chain all voice processing stages together.

        Args:
            stream: Input token stream.

        Returns:
            Token stream synchronized with speech output.
        """
        tagged_stream = self.mute_tag_processor.process(stream)
        analyzed_stream= self.mute_analyzer.process(tagged_stream)
        marked_lines = self.line_splitter.process(analyzed_stream)
        lines_with_playback = self.line_to_audio.process(marked_lines)
        synced_stream=self.speech_processor.process(lines_with_playback)
        throttled_stream=self.throttler.process(synced_stream)
        return throttled_stream            

