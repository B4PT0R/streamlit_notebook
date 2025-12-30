from .utils import root_join, text_content, total_tokens, NoContext, add_line_numbers, sort, timestamp, short_id, session_id, guess_extension_from_bytes, truncate, read_document_content, ThreadPool
from modict import modict
import json
import os
import shutil
from io import BytesIO
import mimetypes
from .message import Message
from .image import Image
from .tool import Tool
from .ai import AIClient
from .voice import VoiceProcessor
from .latex import LaTeXProcessor
from .stream_utils import MarkdownBlockExtractor
from pynteract import Shell
from datetime import datetime
from typing import List


def default_process_text_chunk(token,content):
    """Default function that prints streamed response tokens to stdout for visualization purposes.

    Args:
        token: The latest token streamed by the model.
        content: The entire content seen so far in the stream.
    """
    print(token,end='',flush=True)


def to_message(d):
    if d.get('type')=="image":
        return Image(d)
    else:
        return Message(d)

class AgentConfig(modict):

    _config = modict.config(enforce_json=True)

    model="gpt-4.1-mini"
    system="You are a helpful AI assistant."
    auto_proceed=True
    openai_api_key=None
    history=None
    name="Pandora"
    username="Unknown"
    userage="Unknown"
    token_limit=128000,
    max_completion_tokens=4000
    max_input_tokens=8000
    reasonning_effort="medium"
    vision_enabled=True
    voice_model='gpt-4o-mini-tts'
    voice="nova"
    voice_instructions="You speak with a friendly and intelligent tone."
    voice_enabled=True
    voice_buffer_size=2
    workfolder=modict.factory(lambda :os.path.expanduser("~/agent_workfolder"))

class Agent:

    def __init__(self,shell=None,**kwargs):
        """Initializes the Agent instance with configuration, OpenAI client, hooks, tools, and message history.

        Args:
            shell: Optional shell instance for code execution. If None, creates a new Shell.
            **kwargs: Additional keyword arguments to update the agent configuration.
        """
        self.config=AgentConfig(kwargs)
        self.hooks=modict()
        self.tools=modict()
        self.current_session_id=None
        self.messages=[]
        self.pending=[] # to store messages created by tool calls temporarily
        self.shell=None
        self.init_shell(shell=shell)
        self.init_workfolder()
        self.init_session_folder()
        self.ai=AIClient(self)
        self.voice=VoiceProcessor(self)
        self.latex=LaTeXProcessor()
        self.md_extractor=MarkdownBlockExtractor()
        self.stream_processors=modict(
            content=[self.voice,self.latex]
        )
        self.init_native_tools()

    def init_workfolder(self):
        if not os.path.isdir(self.config.workfolder):
            os.makedirs(self.config.workfolder,exist_ok=True)

    def init_shell(self,shell=None):
        if shell is None:
            if self.hooks.get("get_shell_hook") is not None:
                shell=self.hooks.get_shell_hook()
            else:
                shell=Shell()
        shell.update_namespace(
            __agent__=self,
            os=os,
        )
        self.shell=shell

    def init_session_folder(self):
        session_folder=os.path.join(self.config.workfolder,'sessions')
        if not os.path.isdir(session_folder):
            os.makedirs(session_folder,exist_ok=True)

    def save_config(self):
        config_file=os.path.join(self.config.workfolder,'agent_config.json')
        self.config.dump(config_file,indent=2, ensure_ascii=False)

    def load_config(self):
        config_file=os.path.join(self.config.workfolder,'agent_config.json')
        if os.path.isfile(config_file):
            self.config.update(self.config.load(config_file))

    def init_native_tools(self):
        """Initialize native tools that are built into the agent.

        These tools (read, run_code, observe) are automatically available to the agent.
        """
        self.add_tool(self.read)
        self.add_tool(self.run_code)
        self.add_tool(self.observe)

    def get_sessions(self):
        """Get list of all available session IDs"""
        session_folder=os.path.join(self.config.workfolder,'sessions')
        if not os.path.isdir(session_folder):
            return []
        session_files=[f for f in os.listdir(session_folder) if f.endswith('.json')]
        return sorted([f.replace('.json','') for f in session_files], reverse=True)

    def load_session(self, session_id):
        """Load a session from storage"""
        self.messages.clear()
        path=os.path.join(self.config.workfolder,'sessions',f"{session_id}.json")
        if os.path.exists(path):
            with open(path,'r',encoding="utf-8") as f:
                data=json.load(f)
            for msg in data:
                self.messages.append(to_message(msg))
        self.current_session_id = session_id
        self.new_message(
            role="system",
            content=f"Resuming chat session at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."
        )

    def start_new_session(self):
        """Start a new session with a unique ID"""
        self.messages.clear()
        self.current_session_id = session_id()
        self.new_message(
            role="system",
            content=f"Starting a new chat session at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."
        )

    def save_session(self):
        """Save current session to storage"""
        if not self.current_session_id:
            return
        messages_to_save = list(map(lambda m:m.exclude('b64_string') if isinstance(m,Image) else m,self.messages))
        path=os.path.join(self.config.workfolder,'sessions',f"{self.current_session_id}.json")
        with open(path,'w',encoding="utf-8") as f:
            json.dump(messages_to_save,f,ensure_ascii=False,indent=2)
        
    def get_system_message(self):
        """Returns the system message for the agent from file or string according to configuration.

        Returns:
            Message: The system message with role='system'.
        """
        if not self.config.get('system'):
            return Message(role="system",content="You are a helpful AI assistant.")
        elif os.path.isfile(self.config.system):
            return Message(role="system",content=text_content(self.config.system))
        elif isinstance(self.config.system,str):
            return Message(role="system",content=self.config.system)
        else:
            raise ValueError(f"Invalid system message configuration. Expected path or string, got {type(self.config.system)}")

    def add_message(self,msg,pending=False):
        """Adds a message to the agent's message list and triggers show_message hook if present.

        Args:
            msg: The message object to add.
            pending: If True, the message is temporarily stored in the pending list.
                Pending messages are processed after tool calls only.
        """
        if pending:
            self.pending.append(msg)
        else:
            # Assign current session_id if message doesn't have one
            if not msg.session_id:
                msg.session_id=self.current_session_id
            self.messages.append(msg)
            self.save_session()
            if self.hooks.get('process_message'):
                self.hooks.process_message(msg)
        return msg
    

    def new_message(self,pending=False,**kwargs):
        """Helper to create and add a message based on provided keyword arguments.

        Args:
            pending: If True, stores message in pending list instead of main messages.
            **kwargs: Message fields as keyword arguments (role, content, etc.).

        Returns:
            The created message object.
        """
        msg=Message(kwargs)
        return self.add_message(msg,pending=pending)
    
    def add_image(self,source,pending=False,**kwargs):
        if source:
            img=Image(
                source=source,
                **kwargs
            )
            self.add_message(img,pending=pending)

    def add_tool(self,func,name=None,description=None,parameters=None,required=None):
        """Registers a new tool for the agent, wrapping a function and its metadata.

        Can be used as a decorator or called directly.

        Args:
            func: The function implementing the tool.
            name: Optional name for the tool. If None, uses function name.
            description: Optional description for the tool.
            parameters: Optional parameters schema for the tool.
            required: Optional required fields for the tool.

        Returns:
            The function (to support decorator syntax).
        """
        tool=Tool(func, name, description, parameters, required)
        self.tools[tool.name]=tool
        return func  # Return func to support decorator syntax

    def get_messages(self,filter=None):
        if filter:
            return [msg for msg in self.messages if filter(msg)]
        return list(self.messages)

    def get_context(self):
        """Builds and returns the full prompt context with system message, images, and windowed history.

        Truncates individual non-image messages to max_input_tokens to prevent token overflow.

        Returns:
            List of formatted messages forming the complete context.
        """
        max_input_tokens = self.config.get('max_input_tokens', 8000)

        system=[self.get_system_message()]

        tools=[tool.to_system_message() for tool in self.get_tools(filter=(lambda tool: not tool.mode=='api'))]

        custom_msgs=self.hooks.custom_messages_hook() if self.hooks.get('custom_messages_hook') else []

        max_images=self.config.get('max_images',1)

        images=[] if not self.config.get('vision_enabled',False) else self.get_messages(filter=lambda msg:isinstance(msg,Image))[-max_images:]

        others=self.get_messages(filter=lambda msg:not isinstance(msg,Image))

        # Truncate individual non-image messages to prevent accidents
        truncated_others = []
        for msg in others:
            msg_copy = msg.copy()
            if msg_copy.get('content') and isinstance(msg_copy.content, str):
                msg_copy.content = truncate(msg_copy.content, max_tokens=max_input_tokens)
            truncated_others.append(msg_copy)

        current_count=total_tokens(system+tools+images+custom_msgs)
        available_tokens=self.config.token_limit - self.config.max_completion_tokens - current_count
        for i,msg in enumerate(reversed(truncated_others)):
            msg_count=total_tokens([msg])
            if current_count+msg_count<=available_tokens:
                current_count+=msg_count
            else:
                break
        history=truncated_others[max(0,len(truncated_others)-i-1):]
        context=system+tools+sort(history+images+custom_msgs)
        return list(msg.format(context=self.shell.namespace) for msg in context) 

    def get_tools(self, filter=None)->List[Tool]:
        """Retrieves tools from the agent's tool registry, optionally filtered by a predicate function.

        Args:
            filter: Optional predicate function to filter tools.

        Returns:
            List of Tool objects matching the filter criteria.
        """
        filter=filter or (lambda tool: True)
        return list(tool for tool in self.tools.values() if filter(tool))

    def aggregate_md_tool_calls(self,message):
        tool_calls = []

        for tc in self.md_extractor.matchs:
            # On part de attrs (dict), qu’on copie pour ne pas muter l’original
            tc = modict(tc)
            # On ajoute le content comme argument séparé si tu veux

            if tc.name in self.tools:

                tool_call = {
                    "id": f"mardown_block_call_{short_id(8)}",
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.args, ensure_ascii=False),
                    },
                    "index": len(tool_calls),  # utile si tu veux le champ index
                }

                tool_calls.append(tool_call)

        if tool_calls:
            message.setdefault('tool_calls',[]).extend(tool_calls)

        return message


    def get_response(self):
        """Streams and aggregates the response content from OpenAI.

        Forwards each token via hook if defined. If tool calls are present, records them along
        with the reply.

        Returns:
            Message: The aggregated assistant message with content and/or tool calls.
        """
        streams=self.ai.stream(
            messages=self.get_context(),
            tools=self.get_tools(filter=(lambda tool: tool.mode=='api')),
            **self.config.extract('model','temperature','max_completion_tokens','top_p','frequency_penalty','presence_penalty','stop','reasoning_effort')
        )

        if self.hooks.get('process_reasoning_stream'):
            self.hooks.process_reasoning_stream(streams.reasoning)
        elif self.hooks.get('process_reasoning_chunk'):
            content=''
            for reasoning_chunk in streams.reasoning:
                content+=reasoning_chunk
                self.hooks.process_reasoning_chunk(reasoning_chunk,content)        

        if self.hooks.get('process_content_stream'):
            self.hooks.process_content_stream(streams.content)
        elif self.hooks.get('process_content_chunk'):
            content=''
            for text_chunk in streams.content:
                content+=text_chunk
                self.hooks.process_content_chunk(text_chunk,content)

        if self.hooks.get('process_tool_calls_stream'):
            self.hooks.process_tool_calls_stream(streams.tool_calls)
        elif self.hooks.get('process_tool_call_chunk'):
            for tool_call_chunk in streams.tool_calls:
                self.hooks.process_tool_call_chunk(tool_call_chunk)

        if self.hooks.get('process_message_stream'):
            self.hooks.process_message_stream(streams.message)
        elif self.hooks.get('process_message_chunk'):
            for message_chunk in streams.message:
                self.hooks.process_message_chunk(message_chunk)

        message=next(iter(streams.final_message))
        
        message=self.aggregate_md_tool_calls(message)

        return self.add_message(message)

    def call_tools(self,message):
        """
        description: |
            Executes any pending tool calls and adds their output to the message history. Handles tool resolution and exceptions.
        """
        called_tools=False
        if message.get('tool_calls'):
            tool_call_context=self.hooks.get('tool_call_context',NoContext)
            for tool_call in message.tool_calls:
                tool=self.tools.get(tool_call.function.name)
                with tool_call_context(tool_call):
                    if tool:
                        try:
                            content=str(tool(**json.loads(tool_call.function.arguments)))
                        except Exception as e:
                            content=f"Error: {str(e)}"
                    else:
                        content=f"Error: Tool '{tool_call.function.name}' not found."
                self.new_message(role="tool",name=tool_call.function.name,tool_call_id=tool_call.id,content=content)
                called_tools=True
        return called_tools

    def add_pending(self):
        """Adds all pending messages to the message history."""
        if self.pending:
            for msg in self.pending:
                msg.timestamp=timestamp()
                self.add_message(msg)
            self.pending=[]
                        
    def process(self):
        """Processes a full turn: gets a response, handles tool calls, and repeats if needed.

        Returns:
            bool: True if agent has finished, False if it needs another turn for tool processing.
        """

        self.add_pending()
        message=self.get_response()
        ThreadPool.join_all()
        called_tools=self.call_tools(message)
        self.add_pending()

        if called_tools:
            if self.config.get('auto_proceed',True):
                return self.process()
            else:
                return False # indicates the agent wants one more turn to continue processing
        return True # indicates the agent has finished its process cycle

    def run_code(self,content=None):
        """
        description: |
            Runs python code in the notebook shell
        parameters:
            content:
                description: The python code to run
        required:
            - content
        """
        if self.shell is not None and content:
            response=self.shell.run(content)
            if response.exception:
                exception=response.exception
                return f"**{type(exception).__name__}**: {str(exception)}\n```\n{exception.enriched_traceback_string}\n```"
            else:
                output=""
                if response.stdout:
                    output+=f"stdout:\n{response.stdout}"
                if response.result:
                    output+=f"result:\n{str(response.result)}"
                return output

        return "Notebook not initialized. Cannot run code."

    def speak(self,text,**kwargs):
        from .voice import silent_play
        audio=self.ai.text_to_audio(text,**kwargs)
        if self.hooks.get('audio_playback_hook'):
            self.hooks.audio_playback_hook(audio)
        else:
            silent_play(audio)

    def listen(self, source, language=None, **kwargs):
        """
        description: |
            Listen to audio input and transcribe it to text, then process it as a user message.
            Accepts either audio data (BytesIO/bytes) or a file path.
        parameters:
            source:
                description: Audio data as file_path string, BytesIO object or bytes
            language:
                description: ISO-639-1 language code (e.g., "en", "fr")
            kwargs:
                description: Additional parameters for the transcription (model, prompt, temperature, etc.)
        """

        transcribed_text = self.transcribe(source, language, **kwargs)

        # Add transcribed text as a user message
        self.new_message(role="user", content=transcribed_text)

    def transcribe(self, source, language=None, **kwargs):
        """
        description: |
            Transcribe audio to text.
            Accepts either audio data (BytesIO/bytes) or a file path.
        parameters:
            source:
                description: Audio data as file_path string, BytesIO object or bytes
            language:
                description: ISO-639-1 language code (e.g., "en", "fr")
            kwargs:
                description: Additional parameters for the transcription (model, prompt, temperature, etc.)
        """
        if source is None:
            raise ValueError("An audio source must be provided")
        
        # Transcribe audio to text
        transcribed_text = self.ai.audio_to_text(
            source=source,
            language=language,
            **kwargs
        )

        return transcribed_text

    def read(self, source, start_at_line=1):
        """
        description: |
            Read and extract text content from various sources including folders, files, urls or python variables / objects.
            For folders: returns a tree view of the folder structure.
            For files: returns the text content. PDF, DOCX, XLSX, PPTX, ODT, HTML, TXT, and more are supported.
            For urls: returns the text content of the web page (or of the remote file if the url points to a file).
            For python variables / objects: instrospects the object or gives a str repr (available ONLY in progammatic usage via run_code("__agent__.tools.read(source=data)")
            
            For large outputs: The output will be automatically truncated to fit token limits. When truncated, you'll see a message at the end of content indicating the truncated line range to know from where to resume reading.

        parameters:
            source:
                description: |
                    Document source - can be either:
                    - Absolute path to a local folder or file (e.g., "/home/user/document.pdf")
                    - URL (e.g., "https://example.com/report.pdf")
                    - any other data structure, or python variable living in the shell's namespace
            start_at_line:
                description: |
                    Line number to start reading from (1-indexed). Default is 1 (start from beginning).
                    When reading large documents in chunks, set this to continue from where you left off.
                type: integer
        required:
            - source
        """
        max_tokens = self.config.get('max_input_tokens', 8000)
        return read_document_content(source, start_at_line=start_at_line, max_tokens=max_tokens)

    def observe(self, source):
        """
        description: |
            Observe and analyze an image by adding it to the conversation context.
            The image will be available for visual analysis in the next response.
            Supports local file paths and URLs (http/https).

            Use this tool when you need to see and analyze images, screenshots, diagrams, charts, photos, or any visual content.

        parameters:
            source:
                description: |
                    Image source - can be either:
                    - Absolute file path to a local image file (e.g., "/home/user/image.png")
                    - URL to an image (e.g., "https://example.com/image.jpg")
                type: string
        required:
            - source
        """
        # Add image with pending=True so it doesn't insert between tool call and response
        self.add_image(source=source, pending=True)
        return f"Image from '{source}' has been loaded and is now visible for analysis."

    def upload_file(self, source, name=None):
        """
        description: |
            Upload a file to the agent's workfolder and inform the agent via system message.
            Supports file paths (str), BytesIO objects, or raw bytes.
        parameters:
            source:
                description: File source - can be a file path (str), BytesIO object, or bytes
            name:
                description: Optional name for the file. Required when source is bytes without a name attribute.
                             Can include extension to override detection.
        returns:
            description: Absolute path to the uploaded file
        """
        if source is None:
            raise ValueError("A file source must be provided")

        # Determine source type and extract data
        if isinstance(source, str):
            # Source is a file path
            if not os.path.exists(source):
                raise ValueError(f"File not found: {source}")

            # Use provided name or extract from source path
            if name is None:
                name = os.path.basename(source)

            # Determine extension from source or provided name
            _, source_ext = os.path.splitext(source)
            _, name_ext = os.path.splitext(name)
            extension = name_ext if name_ext else source_ext

            # Construct destination path
            base_name = os.path.splitext(name)[0]
            dest_filename = base_name + extension
            dest_path = os.path.join(self.config.workfolder, dest_filename)

            # Copy file to workfolder
            shutil.copy2(source, dest_path)

        elif isinstance(source, BytesIO):
            # Source is BytesIO
            data = source.getvalue()

            # Determine filename
            if name is None:
                if hasattr(source, 'name'):
                    name = source.name
                else:
                    name = f"uploaded_file_{short_id()}"

            # Determine extension
            _, name_ext = os.path.splitext(name)
            if name_ext:
                extension = name_ext
            else:
                # Guess from content
                extension = guess_extension_from_bytes(data)
                if extension is None:
                    extension = ''

            # Construct destination path
            base_name = os.path.splitext(name)[0]
            dest_filename = base_name + extension
            dest_path = os.path.join(self.config.workfolder, dest_filename)

            # Write bytes to file
            with open(dest_path, 'wb') as f:
                f.write(data)

        elif isinstance(source, bytes):
            # Source is raw bytes
            if name is None:
                name = f"uploaded_file_{short_id()}"

            # Determine extension
            _, name_ext = os.path.splitext(name)
            if name_ext:
                extension = name_ext
            else:
                # Guess from content
                extension = guess_extension_from_bytes(source)
                if extension is None:
                    extension = ''

            # Construct destination path
            base_name = os.path.splitext(name)[0]
            dest_filename = base_name + extension
            dest_path = os.path.join(self.config.workfolder, dest_filename)

            # Write bytes to file
            with open(dest_path, 'wb') as f:
                f.write(source)
        else:
            raise TypeError(f"Unsupported source type: {type(source)}. Expected str, BytesIO, or bytes.")

        # Add system message informing the agent
        self.new_message(
            role="system",
            content=f"File '{dest_filename}' has been uploaded to the workfolder at: {os.path.abspath(dest_path)}"
        )

        return os.path.abspath(dest_path)

    def __call__(self,prompt=None)->bool:
        """Adds the user prompt to the message history and processes the conversation turn.

        Args:
            prompt: The user prompt or query.

        Returns:
            bool: True if the agent has finished, False if it needs to continue.
        """
        if prompt:
            self.new_message(role="user",content=prompt)
        return self.process()

    def interact(self):
        """Starts an interactive command-line loop for user prompts until 'exit' or 'quit' is typed.

        Uses Alt+Enter for multi-line input submission.
        """
        import prompt_toolkit
        print("Starting interactive agent. Type 'exit' or 'quit' to stop.")
        print('Use [Alt+Enter] to submit multi-line input.\n')
        while True:
            try:
                prompt=prompt_toolkit.prompt('You: ', multiline=True)
                print()  # New line after user input
                if prompt.strip().lower() in ['exit','quit']:
                    print("Exiting interactive agent.")
                    break
                print("Agent: ", end='', flush=True)
                self(prompt)
                print()  
                print()  # New lines after agent response
            except (KeyboardInterrupt, EOFError):
                print("\nExiting interactive agent.")
                break
