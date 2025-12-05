import numpy as np
from .message import Message
from collections.abc import Mapping
from .image import Image
from textwrap import dedent
from queue import Queue
from ..adict import adict
import io, os
from openai import OpenAI, OpenAIError
from typing import Union, List
from pydub import AudioSegment
from .utils import Thread
from pydantic import BaseModel

class AIClientError(Exception):
    pass

class AIClient:

    def __init__(self, agent):
        """
        Initialize AI client with OpenAI API key.

        Args:
            api_key: OpenAI API key. If None, will use OPENAI_API_KEY environment variable.
        """
        self.agent=agent
        self._client = None

    @property
    def client(self):
        if self._client is None:
            api_key=self.agent.config.get('openai_api_key') or os.getenv('OPENAI_API_KEY')
            try:
                self._client = OpenAI(api_key=api_key, timeout=180, max_retries=3)
                if not self.api_key_is_valid():
                    self._client=None
                    raise AIClientError("Missing or invalid OpenAI API key. You can pass it when creating the agent with `agent=Agent(openai_api_key='your_api_key')` or set the OPENAI_API_KEY environment variable. You can get an API key at https://platform.openai.com/account/api-keys.")
            except OpenAIError:
                self._client=None
                raise AIClientError("Missing or invalid OpenAI API key. You can pass it when creating the agent with `agent=Agent(openai_api_key='your_api_key')` or set the OPENAI_API_KEY environment variable. You can get an API key at https://platform.openai.com/account/api-keys.")
        return self._client

    def api_key_is_valid(self):
        """
        Verify that the API key is valid by making a minimal API call.

        Returns:
            bool: True if API key is valid, False otherwise
        """
        try:
            # Make a minimal API call to verify the key
            self.client.models.list()
            return True
        except Exception as e:
            return False

    def text_to_audio(self, model=None, voice=None, input='', voice_instructions='', **kwargs):
        """
        Generate speech audio from text using OpenAI TTS.

        Args:
            model: TTS model identifier (default: "gpt-4o-mini-tts")
            voice: OpenAI-style voice name (alloy, echo, fable, onyx, nova, shimmer)
            input: Text to synthesize
            voice_instructions: Tone hint
            **kwargs: Additional parameters

        Returns:
            BytesIO buffer containing MP3 audio
        """
        # Build TTS input
        params = adict(
            model=model or "gpt-4o-mini-tts",
            voice=voice or "nova",
            instructions=voice_instructions or "You speak with a friendly and casual tone.",
            input=input
        )

        # Override with any additional kwargs
        params.update(kwargs)

        # Call OpenAI API
        try:
            mp3_buffer = io.BytesIO()

            response = self.client.audio.speech.create(**params)

            for chunk in response.iter_bytes():
                mp3_buffer.write(chunk)

            mp3_buffer.seek(0)

            audio = AudioSegment.from_file(mp3_buffer,format="mp3").set_channels(1)

            return audio

        except Exception as e:
            raise AIClientError(f"TTS generation failed: {str(e)}")

    def audio_to_text(
        self,
        source: Union[str, io.BytesIO, bytes],
        model: str = "whisper-1",
        language: str = None,
        prompt: str = None,
        response_format: str = "text",
        temperature: float = 0.0
    ) -> str:
        """
        Convert audio to text using OpenAI's Whisper model.

        Args:
            source: Audio data as file_path string, BytesIO object or bytes
            model: Model to use (default: "whisper-1")
            language: ISO-639-1 language code (e.g., "en", "fr"). If None, language is auto-detected.
            prompt: Optional text to guide the model's style
            response_format: Format of output ("text", "json", "verbose_json", "srt", "vtt")
            temperature: Sampling temperature between 0 and 1 (default: 0.0)

        Returns:
            Transcribed text as a string
        """
        if isinstance(source, str) and os.path.isfile(source):
            with open(source, "rb") as f:
                audio = io.BytesIO(f.read())
        elif isinstance(source, bytes):
                audio = io.BytesIO(source)
        elif isinstance(source, io.BytesIO):
            audio = source
        else:
            raise NotImplementedError(f"Unsupported audio source: {source}")

        # Ensure the BytesIO object is at the start
        audio.seek(0)

        # Prepare the file for upload
        audio.name = "audio.mp3"  # Add a name attribute

        # Prepare transcription parameters
        transcription_params = {
            "model": model,
            "file": audio,
            "response_format": response_format,
            "temperature": temperature
        }

        # Add optional parameters if provided
        if language:
            transcription_params["language"] = language
        if prompt:
            transcription_params["prompt"] = prompt

        # Call OpenAI transcription API (retries handled by client)
        try:
            transcript = self.client.audio.transcriptions.create(**transcription_params)
        except Exception as e:
            raise AIClientError(f"Failed to transcribe audio: {str(e)}")

        # Extract text from response
        if response_format == "text":
            return transcript
        elif response_format in ["json", "verbose_json"]:
            return transcript.text
        else:
            # For srt and vtt formats, return as-is
            return transcript
    
    def get_tools_call_by_index(self,message,index):
        for tc in message.get('tool_calls',[]):
            if tc.get('index')==index:
                return tc
        return None
    
    def aggregate_delta(self,delta,message):
        """
        description: |
            Aggregates deltas from streaming response into the message being built.
        parameters:
            delta:
                description: The delta object containing possible tool calls or content.
            message:
                description: The message being built.
        """

        tool_calls_chunk = delta.get('tool_calls')
        text_chunk=delta.get('content') or ''
        reasoning_chunk=delta.get('reasoning') or ''

        # aggregate chunks in current message
        message.content+=text_chunk
        message.reasoning+=reasoning_chunk
        if tool_calls_chunk:
            for tc in delta.tool_calls:
                existing_tc=self.get_tools_call_by_index(message,tc.index)
                if existing_tc is None:
                    message.setdefault('tool_calls',[]).append(tc)
                else:
                    #agregate function arguments
                    args_chunk=tc.get('function',{}).get('arguments','')
                    existing_tc.function.arguments+=args_chunk

        return text_chunk, reasoning_chunk, tool_calls_chunk, message

    def _stream_completion_target(self, params, text_queue, reasoning_queue, tool_calls_queue, msg_queue, assistant_name=None):
        """Private method to handle streaming completion in a separate thread"""
        success=False
        exc=None
        try:
            # Extract reasoning_effort if present
            effort = params.pop('reasoning_effort', None)
            if effort and any(params['model'].startswith(prefix) for prefix in ('o', 'gpt-5')):
                params['reasoning'] = dict(effort=effort)

            # Call OpenAI chat completion API
            response = self.client.chat.completions.create(
                stream=True,
                **params
            )
        except Exception as e:
            exc=e
            success=False
            import traceback
            import sys
            print("\n[ERROR in ai.stream]:", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
        else:
            success=True

        message=Message(role="assistant", name=assistant_name)

        if success:
            for chunk in response:
                if not hasattr(chunk,'choices') or not chunk.choices or not hasattr(chunk.choices[0],'delta'):
                    continue
                delta=chunk.choices[0].delta
                if isinstance(delta,BaseModel):
                    delta=adict.convert(delta.model_dump())
                elif isinstance(delta,Mapping):
                    delta=adict.convert(delta)
                text_chunk,reasoning_chunk,tool_calls_chunk,message=self.aggregate_delta(delta,message)
                if text_chunk: text_queue.put(text_chunk)
                if reasoning_chunk: reasoning_queue.put(reasoning_chunk)
                if tool_calls_chunk: tool_calls_queue.put(tool_calls_chunk)
                msg_queue.put(message)
        else:
            message.content=f"Hmmm, sorry! There was an error while calling the OpenAI client. Here is the error message I got:\n\n ```\n{str(exc)}\n```"
            text_queue.put(message.content)
            msg_queue.put(message)
            print(exc)

        text_queue.put("#END#")
        reasoning_queue.put("#END#")
        msg_queue.put("#END#")

    def stream(self, assistant_name=None, **params):

        text_queue=Queue()
        tool_calls_queue=Queue()
        reasoning_queue=Queue()
        msg_queue=Queue()

        params['messages']=[msg.to_llm_client_format(include_name=True) for msg in params.get('messages',[])]
        params['tools'] = [tool.to_llm_client_format() for tool in params.get('tools') or []] or None

        completion=Thread(
            target=self._stream_completion_target,
            args=(params, text_queue, reasoning_queue, tool_calls_queue, msg_queue, assistant_name)
        )
        completion.start()

        def text_stream():
            while not (text_chunk:=text_queue.get())=="#END#":
                yield text_chunk

        def reasonning_stream():
            while not (reasoning_chunk:=reasoning_queue.get())=="#END#":
                yield reasoning_chunk

        def tool_calls_stream():
            while not (tool_calls_chunk:=tool_calls_queue.get())=="#END#":
                yield tool_calls_chunk

        def msg_stream():
            while not (message:=msg_queue.get())=="#END#":
                yield message


        return text_stream(), reasonning_stream(), tool_calls_stream(), msg_stream()

    def _normalize(self, vect, precision=5):
        """Normalize a vector and round to specified precision."""
        inv_norm = 1.0 / np.linalg.norm(vect, ord=2)
        return [round(x_i * inv_norm, precision) for x_i in vect]

    def embed_content(self, content: str, precision=5, dimensions=128, model="text-embedding-3-small"):
        """
        Embed a text string using OpenAI embeddings.

        Args:
            content: Text string to embed
            precision: Number of decimal places for rounding (default: 5)
            dimensions: Embedding dimensions (default: 128)
            model: OpenAI embedding model to use (default: text-embedding-3-small)

        Returns:
            A normalized embedding vector
        """
        if not isinstance(content, str):
            raise ValueError(f"Content must be a string, got {type(content)}")

        try:
            response = self.client.embeddings.create(
                model=model,
                input=content,
                dimensions=dimensions
            )
            embedding = response.data[0].embedding
        except Exception as e:
            raise AIClientError(f"Failed to generate embedding: {str(e)}")

        return self._normalize(embedding, precision)

    def embed_contents(self, contents: List[str], precision=5, dimensions=128, model="text-embedding-3-small"):
        """
        Embed multiple text strings using OpenAI embeddings.

        Args:
            contents: List of text strings to embed
            precision: Number of decimal places for rounding (default: 5)
            dimensions: Embedding dimensions (default: 128)
            model: OpenAI embedding model to use (default: text-embedding-3-small)

        Returns:
            List of normalized embedding vectors

        Note:
            OpenAI API handles batching automatically for better performance.
        """
        if not all(isinstance(content, str) for content in contents):
            raise ValueError("All contents must be strings")

        try:
            response = self.client.embeddings.create(
                model=model,
                input=contents,
                dimensions=dimensions
            )
            embeddings = [self._normalize(item.embedding, precision) for item in response.data]
        except Exception as e:
            raise AIClientError(f"Failed to generate embeddings: {str(e)}")

        return embeddings

    def similarity(self, emb1, emb2):
        """
        Calculate shifted positive cosine similarity between two embeddings.
        Returns a score between 0 and 1.
        """
        return 0.5 + 0.5 * np.dot(np.array(emb1), np.array(emb2))

    def embed_message(self, msg, precision=5, dimensions=128, model="text-embedding-3-small"):
        """
        Embed a Message object and assign the result to msg.embedding.

        Args:
            msg: Message object with text content
            precision: Number of decimal places for rounding (default: 5)
            dimensions: Embedding dimensions (default: 128)
            model: OpenAI embedding model to use (default: text-embedding-3-small)

        Returns:
            The embedding vector (also assigned to msg.embedding)

        Note:
            Only text content is supported.
        """
        if hasattr(msg, 'content') and isinstance(msg.content, str):
            content = msg.content
        else:
            raise ValueError("Message must have text content")

        # Generate embedding
        embedding = self.embed_content(content, precision, dimensions, model)

        # Assign to msg.embedding
        msg.embedding = embedding

        return embedding




