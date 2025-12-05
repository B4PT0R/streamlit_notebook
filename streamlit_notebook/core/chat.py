import streamlit as st
from .utils import root_join, rerun, short_id
import os
import json
from ..core.notebook import get_notebook
from datetime import datetime
from .auto_play import auto_play

# Optional agent imports
try:
    from ..agent import Agent, Message
    from ..agent.ai import AIClientError
    HAS_AGENT = True
except ImportError:
    HAS_AGENT = False
    Agent = None
    Message = None
    AIClientError = Exception  # Fallback to base Exception

state=st.session_state

def audio_playback_backend(audio_buffer):
    auto_play(audio_buffer)

def get_default_system_prompt():
    """Load default system prompt from system_prompt.txt"""
    system_prompt_path = root_join('agent', 'prompts', 'system_prompt.txt')
    if os.path.exists(system_prompt_path):
        with open(system_prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "You are a helpful AI assistant."

# Default settings
DEFAULT_SETTINGS = {
    "model": "gpt-4.1-mini",
    "temperature": 1.0,
    "max_completion_tokens": 4000,
    "max_input_tokens":8000,
    "token_limit": 128000,
    "username": "Unknown",
    "userage": "Unknown",
    "reasoning_effort": "medium",
    "vision_enabled": True,
    "voice_enabled": False,
    "voice_model": "gpt-4o-mini-tts",
    "voice": "nova",
    "voice_instructions": "You speak with a friendly and intelligent tone.",
    "show_tool_calls": True,
    "system_prompt": get_default_system_prompt(),
    "openai_api_key": None,
}

def load_settings(agent):
    """Load settings from agent_workfolder/settings.json"""
    settings_path = os.path.join(agent.config.workfolder, "settings.json")
    if os.path.exists(settings_path):
        with open(settings_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return DEFAULT_SETTINGS.copy()

def save_settings(agent, settings):
    """Save settings to agent_workfolder/settings.json"""
    settings_path = os.path.join(agent.config.workfolder, "settings.json")
    with open(settings_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

@st.dialog("Settings", width="large")
def settings_dialog():
    """Dialog for chat and agent settings"""
    st.write("### Chat and Agent Settings")

    # Create two main columns
    left_col, right_col = st.columns(2)

    with left_col:
        st.write("#### User & API")
        # User details - horizontal
        with st.container():
            c1, c2 = st.columns(2)
            with c1:
                username=st.text_input("Your name", value=state.agent.config.get("username", "Unknown"))
            with c2:
                userage=st.text_input("Your age", value=state.agent.config.get("userage", "Unknown"))

        # OpenAI API Key
        current_api_key = state.agent.config.get("openai_api_key", "") or ""
        api_key = st.text_input(
            "OpenAI API Key",
            value=current_api_key,
            type="password",
            help="Leave empty to use OPENAI_API_KEY environment variable"
        )

        st.divider()
        st.write("#### Model Settings")

        # Model and Reasoning - horizontal
        with st.container():
            c1, c2 = st.columns(2)
            with c1:
                model = st.selectbox(
                    "Model",
                    ["gpt-4.1-mini", "gpt-4.1", "gpt-4o", "gpt-4o-mini", "o1-preview", "o1-mini"],
                    index=["gpt-4.1-mini", "gpt-4.1", "gpt-4o", "gpt-4o-mini", "o1-preview", "o1-mini"].index(state.agent.config.get("model", "gpt-4.1-mini"))
                )
            with c2:
                reasoning_effort = st.selectbox(
                    "Reasoning Effort",
                    ["low", "medium", "high"],
                    index=["low", "medium", "high"].index(state.agent.config.get("reasoning_effort", "medium"))
                )

        # Temperature
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=state.agent.config.get("temperature", 0.7),
            step=0.1
        )

        st.divider()
        st.write("#### Token Limits")

        # Token limits - 3 columns
        with st.container():
            c1, c2, c3 = st.columns(3)
            with c1:
                max_tokens = st.number_input(
                    "Max Completion",
                    min_value=100,
                    max_value=16000,
                    value=state.agent.config.get("max_completion_tokens", 4000),
                    step=100
                )
            with c2:
                max_input_tokens = st.number_input(
                    "Max Input",
                    min_value=4000,
                    max_value=32000,
                    value=state.agent.config.get("max_input_tokens", 8000),
                    step=1000
                )
            with c3:
                token_limit = st.number_input(
                    "Token Limit",
                    min_value=1000,
                    max_value=200000,
                    value=state.agent.config.get("token_limit", 128000),
                    step=1000
                )

    with right_col:
        st.write("#### Features")

        # Checkboxes - horizontal
        with st.container():
            c1, c2 = st.columns(2)
            with c1:
                vision_enabled = st.checkbox(
                    "Vision Enabled",
                    value=state.agent.config.get("vision_enabled", True)
                )
            with c2:
                show_tool_calls = st.checkbox(
                    "Show Tool Calls",
                    value=state.get("show_tool_calls", True)
                )

        st.divider()
        st.write("#### Voice Settings")

        # Voice enabled
        voice_enabled = st.checkbox(
            "Voice Enabled",
            value=state.agent.config.get("voice_enabled", False)
        )

        # Voice model and voice - horizontal
        with st.container():
            c1, c2 = st.columns(2)
            with c1:
                voice_model = st.selectbox(
                    "Voice Model",
                    ["gpt-4o-mini-tts", "gpt-4o-tts"],
                    index=["gpt-4o-mini-tts", "gpt-4o-tts"].index(state.agent.config.get("voice_model", "gpt-4o-mini-tts"))
                )
            with c2:
                voice = st.selectbox(
                    "Voice",
                    ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
                    index=["alloy", "echo", "fable", "onyx", "nova", "shimmer"].index(state.agent.config.get("voice", "nova"))
                )

        # Voice instructions
        voice_instructions = st.text_area(
            "Voice Instructions",
            value=state.agent.config.get("voice_instructions", "You speak with a friendly and intelligent tone."),
            height=80
        )

    # System prompt - full width at the bottom, outside columns
    st.divider()
    st.write("#### System Prompt")

    current_system = state.agent.config.get("system", "")
    if os.path.isfile(current_system):
        with open(current_system, 'r', encoding='utf-8') as f:
            current_system_content = f.read()
    else:
        current_system_content = current_system if isinstance(current_system, str) else get_default_system_prompt()

    system_prompt = st.text_area(
        "System Prompt",
        value=current_system_content,
        height=120,
        label_visibility="collapsed"
    )


    # Buttons at the bottom
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Save", type="primary", width='stretch'):
            # Apply settings to agent config
            state.agent.config.username=username
            state.agent.config.userage=userage
            state.agent.config.model = model
            state.agent.config.temperature = temperature
            state.agent.config.max_completion_tokens = max_tokens
            state.agent.config.max_input_tokens = max_input_tokens
            state.agent.config.token_limit = token_limit
            state.agent.config.reasoning_effort = reasoning_effort
            state.agent.config.vision_enabled = vision_enabled
            state.agent.config.voice_enabled = voice_enabled
            state.agent.config.voice_model = voice_model
            state.agent.config.voice = voice
            state.agent.config.voice_instructions = voice_instructions
            state.agent.config.system = system_prompt
            state.show_tool_calls = show_tool_calls

            # Apply API key (None if empty string)
            state.agent.config.openai_api_key = api_key if api_key.strip() else None

            # Save to settings file (don't save the API key for security)
            new_settings = {
                "model": model,
                "temperature": temperature,
                "max_completion_tokens": max_tokens,
                "token_limit": token_limit,
                "reasoning_effort": reasoning_effort,
                "vision_enabled": vision_enabled,
                "voice_enabled": voice_enabled,
                "voice_model": voice_model,
                "voice": voice,
                "voice_instructions": voice_instructions,
                "show_tool_calls": show_tool_calls,
                "system_prompt": system_prompt,
            }
            save_settings(state.agent, new_settings)

            st.success("Settings saved!")
            rerun(wait=False)

    with col2:
        if st.button("Cancel", width='stretch'):
            rerun(wait=False)

def init_chat():
    """Initialize the chat agent.

    Returns:
        bool: True if agent was initialized successfully, False if agent module not available
    """
    if not HAS_AGENT:
        return False

    if not state.get("chat_initialized",False):
        workfolder = os.path.expanduser("~/agent_workfolder")

        # Create agent with default settings first
        state.agent=Agent(
            model="gpt-4.1-mini",
            system=root_join('agent','prompts','system_prompt.txt'),
            vision_enabled=True,
            voice_instructions="You speak with an intelligent and friendly tone. Always ready to tackle new coding challenges.",
            workfolder=workfolder
        )

        # Load and apply saved settings
        settings = load_settings(state.agent)
        state.agent.config.model = settings.get("model", "gpt-4.1-mini")
        state.agent.config.temperature = settings.get("temperature", 0.7)
        state.agent.config.max_completion_tokens = settings.get("max_completion_tokens", 4000)
        state.agent.config.token_limit = settings.get("token_limit", 128000)
        state.agent.config.reasoning_effort = settings.get("reasoning_effort", "medium")
        state.agent.config.vision_enabled = settings.get("vision_enabled", True)
        state.agent.config.voice_enabled = settings.get("voice_enabled", False)
        state.agent.config.voice_model = settings.get("voice_model", "gpt-4o-mini-tts")
        state.agent.config.voice = settings.get("voice", "nova")
        state.agent.config.voice_instructions = settings.get("voice_instructions", "You speak with a friendly and intelligent tone.")
        state.show_tool_calls = settings.get("show_tool_calls", True)

        state.agent.hooks.show_text_stream=show_text_stream
        state.agent.hooks.show_message=show_message
        state.agent.hooks.audio_playback_hook=audio_playback_backend

        def custom_notebook_messages():
            notebook=get_notebook()
            if notebook:
                content=json.dumps(notebook.get_info(),indent=2, ensure_ascii=False)
                return [Message(role="system",name="notebook_state",content=f"Here is the current notebook state:\n{content}")]
            else:
                return []

        state.agent.hooks.custom_messages_hook=custom_notebook_messages

        @state.agent.add_tool
        def run_code(code):
            """
            description: |
                Runs python code in the notebook shell
            parameters:
               code:
                    description: The python code to run
            required:
                - code
            """
            notebook=get_notebook()
            if notebook:
                response=notebook.shell.run(code)
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

        # Always start with a new session
        state.agent.start_new_session()

        # Inject agent into shell namespace so it's accessible as __agent__
        notebook = get_notebook()
        if notebook and notebook.shell:
            notebook.shell.update_namespace(__agent__=state.agent)

        state.chat_initialized=True

    return True

def avatar(role):
    """
    description: |
        Returns the avatar image path for a given conversation role.
    parameters:
        role:
            description: The role in the conversation (user, assistant, tool, etc.)
    required:
        - role
    """
    if role == 'user':
        return root_join('app_images', 'user_avatar.png')
    elif role == 'assistant':
        return root_join('app_images', 'assistant_avatar.png')
    elif role == 'system':
        return root_join('app_images', 'system_avatar.png')
    else:
        return None  # Use Streamlit default for other roles

def show_message(msg):
    """
    description: |
        Displays a message (user, assistant, or tool) in the UI, adapting layout according to its role and optionally expanding tool calls.
    parameters:
        msg:
            description: The message object to be displayed.
    required:
        - msg
    """
    if not state.get('chat_initialized'):
        return
    
    state.stream_area.empty()

    # Check if we should show tool calls
    show_tools = state.get('show_tool_calls', False)

    if msg.role in ['user','assistant'] and not msg.type=='image':
        # Check if there's actual content to display
        has_content = msg.content and msg.content.strip()
        has_tool_calls = msg.get('tool_calls') and show_tools

        # Don't show empty messages (only tool calls without content when tools are not hidden)
        if not has_content and not has_tool_calls:
            return

        with state.chat_area:
            with st.chat_message(name=msg.role, avatar=avatar(msg.role)):
                if has_tool_calls:
                    for tool_call in msg.tool_calls:
                        with st.expander(f"🔧 Tool Call: {tool_call.function.name}"):
                            st.markdown(f"**Arguments:**")
                            st.json(tool_call.function.arguments)
                if has_content:
                    st.markdown(msg.content)

    elif msg.type=='image':
        with state.chat_area:
            st.image(msg.as_bytesio(),width='stretch')

    elif msg.role=='tool':
        if show_tools:
            with state.chat_area:
                with st.expander(f'🔧 Tool Response: {msg.name}'):
                    st.text(f"{msg.content}")


def show_session():
    """
    description: |
        Iterates through the session message history and displays each message in the UI.
    """
    for msg in state.agent.messages:
        if msg.session_id==state.agent.current_session_id:
            show_message(msg)


def show_text_stream(token,buffer):
    if not state.get('chat_initialized'):
        return
    with state.stream_area:
        with st.chat_message("assistant",avatar=avatar("assistant")):
            st.write(buffer)

def show_chat():
    """Display the AI chat interface.

    Shows a friendly error message if the agent module is not installed.
    """
    if not init_chat():
        st.error("**AI Agent not available**")
        st.info(
            "The AI agent module is not installed. To enable the chat feature, install with:\n\n"
            "```bash\n"
            "pip install streamlit_notebook[agent-full]\n"
            "```"
        )
        def on_back_click():
            state.chat_mode = False
        st.button("← Back to Notebook", on_click=on_back_click, width='stretch', type='tertiary', key="button_back_to_notebook")
        return

    # session management and settings

    with st.container(border=True): 
        col1, col2 = st.columns(2)

        with col1:
            # Session selector
            sessions = state.agent.get_sessions()
            if sessions:
                selected_session = st.selectbox(
                    "Sessions",
                    options=sessions,
                    format_func=lambda x: x.replace('.json', '') if x.endswith('.json') else x,
                    index=sessions.index(state.agent.current_session_id) if state.agent.current_session_id in sessions else 0,
                    key="session_selector",
                    label_visibility="collapsed"
                )

                # Load selected session if different from current
                if selected_session != state.agent.current_session_id:
                    state.agent.load_session(selected_session)
                    rerun()

        with col2:
            # New session button
            if st.button("➕ New Session", width='stretch', help="Démarrer une nouvelle session"):
                state.agent.start_new_session()
                rerun()

        # Settings button
        if st.button("⚙️ Settings", width='stretch', help="Chat and AI settings"):
            settings_dialog()

    

    # Chat area

    with st.container(horizontal=True, horizontal_alignment='center'):
        st.space(size='stretch')
        st.image(root_join("app_images", "pandora_logo.png"),caption="# **Hey! I'm Pandora!**",width=300)
        st.space(size='stretch')

    state.chat_area=st.container()
    state.stream_area=st.empty()

    with state.chat_area:
        show_session()

    # input area
    with st.container(border=True):
        # Chat input
        prompt=st.chat_input("Ask me anything")
        
        with st.container(horizontal=True):
            # audio input
            with st.container(width=47):
                def on_change():
                    state.new_stt_audio_bytes=True
                    state.stt_audio_bytes=state[state.audio_input_key]
                    state.audio_input_key=f"audio_input_{short_id()}"
                st.audio_input("Record your voice", key=state.setdefault('audio_input_key',f"audio_input_{short_id()}"), on_change=on_change, width=47, label_visibility="collapsed")
            # file upload
            with st.container(width='stretch'):
                def on_change():
                    uploaded_files=state[state.file_uploader_key]
                    state.file_uploader_key=f"file_uploader_{short_id()}"
                    if isinstance(uploaded_files,list):
                        for file in uploaded_files:   
                            state.agent.upload_file(file)
                st.file_uploader("Upload files", key=state.setdefault("file_uploader_key",f"file_uploader_{short_id()}"), on_change=on_change, label_visibility="collapsed", accept_multiple_files=True)
    
    with state.stream_area:
        try:
            if state.setdefault('new_stt_audio_bytes',False):
                prompt = state.agent.transcribe(state.stt_audio_bytes)
                state.new_stt_audio_bytes=False
            if prompt:
                state.agent(prompt)
        except AIClientError as e:
            with state.chat_area:
                st.warning("AI features (including STT and TTS) can only be used with a valid OpenAI API key. Please set it in '⚙️ Settings' or provide it as an `OPENAI_API_KEY` environment variable. You can get one at https://platform.openai.com/account/api-keys")
        except Exception as e:
            with state.chat_area:
                st.info(f"An error of type: {str(type(e))} occured.")
                st.error(f"Error: {e}")

    # Back to notebook button
    def on_back_click():
        state.chat_mode = False
    st.button("← Back to Notebook", on_click=on_back_click, width='stretch', type='tertiary', key="button_back_to_notebook")


