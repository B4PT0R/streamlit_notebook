import streamlit as st
from .utils import root_join, short_id, state_key
from .rerun import rerun
import os
import json
from ..core.notebook import get_notebook
from datetime import datetime
from .components.auto_play import auto_play
from modict import modict

# Optional agent imports
try:
    from ..agent import Agent, Message
    from ..agent.ai import AIClientError, APIAuthenticationError
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
    """Load settings from agent_workfolder/settings.json with defaults"""
    settings_path = os.path.join(agent.config.workfolder, "settings.json")
    settings = DEFAULT_SETTINGS.copy()
    if os.path.exists(settings_path):
        with open(settings_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
            settings.update(loaded)
    return settings

def save_settings(agent, settings):
    """Save settings to agent_workfolder/settings.json"""
    settings_path = os.path.join(agent.config.workfolder, "settings.json")
    with open(settings_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

@st.dialog("Chat & Agent Settings", width="large")
def settings_dialog():
    """Dialog for chat and agent settings"""

    # Create two main columns
    left_col, right_col = st.columns(2)
    agent = state[state_key("agent")]

    with left_col:
        
        # User details - horizontal
        with st.container(border=True, gap="small"):
            st.write("#### User & API")
            c1, c2 = st.columns(2, gap="small")
            with c1:
                username=st.text_input(
                    "Your name",
                    value=agent.config.get("username", "Unknown"),
                    key=state_key("chat_settings_username"),
                )
            with c2:
                userage=st.text_input(
                    "Your age",
                    value=agent.config.get("userage", "Unknown"),
                    key=state_key("chat_settings_userage"),
                )

            # OpenAI API Key
            current_api_key = agent.config.get("openai_api_key", "") or ""
            api_key = st.text_input(
                "OpenAI API Key",
                value=current_api_key,
                type="password",
                help="Leave empty to use OPENAI_API_KEY environment variable",
                key=state_key("chat_settings_api_key"),
            )

        # Model and Reasoning - horizontal
        with st.container(border=True, gap="small"):
            st.write("#### Model Settings")
            c1, c2 = st.columns(2, gap="small")
            with c1:
                model = st.selectbox(
                    "Model",
                    ["gpt-5.1", "gpt-5.1-mini", "gpt-4.1-mini", "gpt-4.1", "gpt-4o", "gpt-4o-mini", "o4-mini", "o3"],
                    index=["gpt-5.1", "gpt-5.1-mini", "gpt-4.1-mini", "gpt-4.1", "gpt-4o", "gpt-4o-mini", "o4-mini", "o3"].index(agent.config.get("model", "gpt-4.1-mini")),
                    key=state_key("chat_settings_model"),
                )
            with c2:
                reasoning_effort = st.selectbox(
                    "Reasoning Effort",
                    ["low", "medium", "high"],
                    index=["low", "medium", "high"].index(agent.config.get("reasoning_effort", "medium")),
                    key=state_key("chat_settings_reasoning_effort"),
                )

            # Temperature
            temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=2.0,
                value=agent.config.get("temperature", 0.7),
                step=0.1,
                key=state_key("chat_settings_temperature"),
            )

        # Token limits - 3 columns
        with st.container(border=True,gap="small"):
            st.write("#### Token Limits")
            c1, c2, c3 = st.columns(3, gap="small")
            with c1:
                max_tokens = st.number_input(
                    "Max Completion",
                    min_value=100,
                    max_value=16000,
                    value=agent.config.get("max_completion_tokens", 4000),
                    step=100,
                    key=state_key("chat_settings_max_completion"),
                )
            with c2:
                max_input_tokens = st.number_input(
                    "Max Input",
                    min_value=4000,
                    max_value=32000,
                    value=agent.config.get("max_input_tokens", 8000),
                    step=1000,
                    key=state_key("chat_settings_max_input"),
                )
            with c3:
                token_limit = st.number_input(
                    "Token Limit",
                    min_value=1000,
                    max_value=200000,
                    value=agent.config.get("token_limit", 128000),
                    step=1000,
                    key=state_key("chat_settings_token_limit"),
                )

    with right_col:
        
        # Checkboxes - horizontal
        with st.container(border=True, gap="small"):
            st.write("#### Features")
            c1, c2, c3 = st.columns(3, gap="small")
            with c1:
                voice_enabled = st.checkbox(
                    "Voice Enabled",
                    value=agent.config.get("voice_enabled", False),
                    key=state_key("chat_settings_voice_enabled"),
                )
            with c2:
                vision_enabled = st.checkbox(
                    "Vision Enabled",
                    value=agent.config.get("vision_enabled", True),
                    key=state_key("chat_settings_vision_enabled"),
                )
            with c3:
                show_tool_calls = st.checkbox(
                    "Show Tool Calls",
                    value=state.get(state_key("show_tool_calls"), True),
                    key=state_key("chat_settings_show_tool_calls"),
                )

        # Voice model and voice - horizontal
        with st.container(border=True, gap="small"):
            st.write("#### Voice Settings")
            c1, c2= st.columns(2, gap="small")

            with c1:
                voice_model = st.selectbox(
                    "Voice Model",
                    ["gpt-4o-mini-tts", "gpt-4o-tts"],
                    index=["gpt-4o-mini-tts", "gpt-4o-tts"].index(agent.config.get("voice_model", "gpt-4o-mini-tts")),
                    key=state_key("chat_settings_voice_model"),
                )
            with c2:
                voice = st.selectbox(
                    "Voice",
                    ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
                    index=["alloy", "echo", "fable", "onyx", "nova", "shimmer"].index(agent.config.get("voice", "nova")),
                    key=state_key("chat_settings_voice"),
                )

            # Voice instructions
            voice_instructions = st.text_area(
                "Voice Instructions",
                value=agent.config.get("voice_instructions", "You speak with a friendly and intelligent tone."),
                height=80,
                key=state_key("chat_settings_voice_instructions"),
            )

        with st.container(border=True, gap="small", height='stretch'):
            # System prompt - full width at the bottom, outside columns
            with st.container(horizontal=True):
                st.write("#### System Prompt")
                st.space(size='stretch')
                if st.button(
                    "🔄 Reset to Default",
                    help="Restore factory default system prompt",
                    key=state_key("chat_settings_reset_system_prompt"),
                ):
                    state[state_key("reset_system_prompt")] = True

            # Initialize reset flag if not present
            reset_prompt_key = state_key("reset_system_prompt")
            if reset_prompt_key not in state:
                state[reset_prompt_key] = False

            current_system = agent.config.get("system", "")
            if os.path.isfile(current_system):
                with open(current_system, 'r', encoding='utf-8') as f:
                    current_system_content = f.read()
            else:
                current_system_content = current_system if isinstance(current_system, str) else get_default_system_prompt()

            # If reset was triggered, use default prompt
            if state[reset_prompt_key]:
                current_system_content = get_default_system_prompt()
                state[reset_prompt_key] = False

            system_prompt = st.text_area(
                "System Prompt",
                value=current_system_content,
                height='stretch',
                label_visibility="collapsed",
                key=state_key("chat_settings_system_prompt"),
            )


    # Save & Cancel buttons at the bottom
    with st.container(horizontal=True):   
        
        st.space(size='stretch')

        # Buttons at the bottom
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Save", type="primary", width='stretch', key=state_key("chat_settings_save")):
                # Apply settings to agent config
                agent.config.username=username
                agent.config.userage=userage
                agent.config.model = model
                agent.config.temperature = temperature
                agent.config.max_completion_tokens = max_tokens
                agent.config.max_input_tokens = max_input_tokens
                agent.config.token_limit = token_limit
                agent.config.reasoning_effort = reasoning_effort
                agent.config.vision_enabled = vision_enabled
                agent.config.voice_enabled = voice_enabled
                agent.config.voice_model = voice_model
                agent.config.voice = voice
                agent.config.voice_instructions = voice_instructions
                agent.config.system = system_prompt
                state[state_key("show_tool_calls")] = show_tool_calls

                # Apply API key (None if empty string)
                agent.config.openai_api_key = api_key if api_key.strip() else None

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
                save_settings(agent, new_settings)

                st.success("Settings saved!")
                rerun(wait=False, debug_msg="chat settings saved")

        with col2:
            if st.button("Cancel", width='stretch', key=state_key("chat_settings_cancel")):
                rerun(wait=False, debug_msg="chat settings cancelled")
    
        st.space(size='stretch')

def init_chat():
    """Initialize the chat agent.

    Returns:
        bool: True if agent was initialized successfully, False if agent module not available
    """
    if not HAS_AGENT:
        return False

    if not state.get(state_key("chat_initialized"), False):
        workfolder = os.path.expanduser("~/agent_workfolder")

        # Create agent with default settings first
        state[state_key("agent")] = Agent(
            model="gpt-4.1-mini",
            system=root_join('agent','prompts','system_prompt.txt'),
            auto_proceed=True,
            workfolder=workfolder
        )

        # Load and apply saved settings
        agent = state[state_key("agent")]
        settings = load_settings(agent)
        agent.config.update(settings)
        state[state_key("show_tool_calls")] = settings.get("show_tool_calls", True)

        agent.hooks.process_content_stream=show_content_stream
        agent.hooks.process_message=show_message
        agent.hooks.audio_playback_hook=audio_playback_backend

        def custom_notebook_messages():
            notebook=get_notebook()
            if notebook:
                content=json.dumps(notebook.get_info(),indent=2, ensure_ascii=False)
                return [Message(role="system",name="notebook_state",content=f"Here is the current notebook state:\n{content}")]
            else:
                return []

        agent.hooks.custom_messages_hook=custom_notebook_messages

        # Always start with a new session
        agent.start_new_session()

        # Inject agent into shell namespace so it's accessible as __agent__
        notebook = get_notebook()
        if notebook and notebook.shell:
            agent.init_shell(notebook.shell)

        state[state_key("chat_initialized")] = True

    return True

def avatar(role):
    """Returns the avatar image path for a given conversation role.

    Args:
        role (str): The role in the conversation (user, assistant, tool, etc.)

    Returns:
        str or None: Path to avatar image, or None for default avatar
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
    """Displays a message (user, assistant, or tool) in the UI.

    Adapts layout according to the message role and optionally expands tool calls.

    Args:
        msg: The message object to be displayed.
    """
    if not state.get(state_key("chat_initialized")):
        return
    
    state[state_key("stream_area")].empty()

    # Check if we should show tool calls
    show_tools = state.get(state_key("show_tool_calls"), False)

    if msg.role in ['user','assistant'] and not msg.type=='image':
        # Check if there's actual content to display
        has_content = msg.content and msg.content.strip()
        has_tool_calls = msg.get('tool_calls') and show_tools

        # Don't show empty messages (only tool calls without content when tools are not hidden)
        if not has_content and not has_tool_calls:
            return

        with state[state_key("chat_area")]:
            with st.chat_message(name=msg.role, avatar=avatar(msg.role)):
                if has_content:
                    st.markdown(msg.content)
                if has_tool_calls:
                    with st.expander(f"🔧 Tool Calls ({len(msg.tool_calls)})"):
                        for tool_call in msg.tool_calls:
                            args=modict.loads(tool_call.function.arguments)
                            with st.container(border=True):
                                if tool_call.function.name=="run_code":
                                    st.code(args.content)
                                else:
                                    st.markdown(f"Calling tool: **{tool_call.function.name}**")    
                                    st.markdown(f"**Arguments:**")
                                    st.json(args)

    elif msg.type=='image':
        with state[state_key("chat_area")]:
            st.image(msg.as_bytesio(),width='stretch')

    elif msg.role=='tool':
        if show_tools:
            with state[state_key("chat_area")]:
                if msg.content.strip():
                    with st.chat_message(name="system", avatar=avatar("system")):
                        with st.expander(f'🔧 Tool Response: {msg.name}'):
                            st.code(msg.content,language="text")


def show_session():
    """Iterates through the session message history and displays each message in the UI."""
    agent = state[state_key("agent")]
    for msg in agent.messages:
        if msg.session_id==agent.current_session_id:
            show_message(msg)


def show_content_stream(stream):
    if not state.get(state_key("chat_initialized")):
        return
    with state[state_key("stream_area")]:
        with st.chat_message("assistant",avatar=avatar("assistant")):
            # Use markdown instead of write for more stable rendering
            st.write_stream(stream)

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
            state[state_key("chat_mode")] = False
        st.button("← Back to Notebook", on_click=on_back_click, width='stretch', type='tertiary', key=state_key("button_back_to_notebook"))
        return

    agent = state[state_key("agent")]

    # session management and settings

    with st.container(border=True):
        col1, col2 = st.columns(2)

        with col1:
            # Session selector
            sessions = agent.get_sessions()
            if sessions:
                st.caption("Load a session")
                selected_session = st.selectbox(
                    "Load a session",
                    options=sessions,
                    format_func=lambda x: x.replace('.json', '') if x.endswith('.json') else x,
                    index=sessions.index(agent.current_session_id) if agent.current_session_id in sessions else 0,
                    key=state_key("session_selector"),
                    label_visibility="collapsed"
                )

                # Load selected session if different from current
                if selected_session != agent.current_session_id:
                    agent.load_session(selected_session)
                    rerun(debug_msg="chat session loaded")

        with col2:
            # New session button
            st.caption("Or create a new one")
            if st.button("➕ New Session", width='stretch', help="Démarrer une nouvelle session", key=state_key("chat_new_session_button")):
                agent.start_new_session()
                rerun(debug_msg="new chat session started")

        if st.button("⚙️ Settings", width='stretch', help="Chat and AI settings", key=state_key("chat_settings_button")):
            settings_dialog()

    # Logo

    with st.container(horizontal=True, horizontal_alignment='center'):
        st.space(size='stretch')
        st.image(root_join("app_images", "pandora_logo.png"),caption="# **Hey! I'm Pandora!**",width=300)
        st.space(size='stretch')   

    # Chat area

    state[state_key("chat_area")] = st.container()
    state[state_key("stream_area")] = st.empty()

    with state[state_key("chat_area")]:
        show_session()

    # Chat input
    prompt=st.chat_input("Ask me anything", accept_audio=True, accept_file="multiple", key=state_key("chat_input"))

    with state[state_key("stream_area")]:
        try:
            if prompt is not None:
                if prompt.files:
                    for file in prompt.files:
                        agent.upload_file(file)
                text=None
                if prompt.audio:
                    text=agent.transcribe(prompt.audio)
                elif prompt.text:
                    text=prompt.text
                if text:
                    agent(text)
        except APIAuthenticationError as e:
            with state[state_key("chat_area")]:
                st.warning("AI features (including STT and TTS) can only be used with a valid OpenAI API key. Please set it in '⚙️ Settings' or provide it as an `OPENAI_API_KEY` environment variable. You can get one at https://platform.openai.com/account/api-keys")
        except Exception as e:
            with state[state_key("chat_area")]:
                st.error(f"Error: {e}")

    # Back to notebook button
    def on_back_click():
        state[state_key("chat_mode")] = False
    st.button("← Back to Notebook", on_click=on_back_click, width='stretch', type='tertiary', key=state_key("button_back_to_notebook"))
