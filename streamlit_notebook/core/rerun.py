import streamlit as st
from .utils import state_key
state = st.session_state

DEBUG = False

def original_rerun(*args,debug_msg=None,**kwargs) -> None:
    """Get the original st.rerun function before patching.

    This function is responsible for clearing the rerun request state
    before triggering the actual rerun.
    """

    if debug_msg and DEBUG:
        print(f"[rerun]: {debug_msg}")

    # Clear any pending rerun request before executing
    # This ensures state never carries over to the next run
    rerun_request_key = state_key("rerun_request")
    if rerun_request_key in state:
        state[rerun_request_key] = None

    if hasattr(st.rerun, '_patched'):
        return st.rerun._original(*args,**kwargs)
    else:
        return st.rerun(*args,**kwargs)

def rerun(scope: str = "app", wait: bool | float = True, debug_msg: str = None) -> None:
    """Command a rerun of the app with optional scope and wait control.

    This function sets a flag in the session state to trigger a rerun
    of the Streamlit app after the current execution is complete.

    When called multiple times during the same run, intelligently merges
    the requests to ensure the longest total delay is respected.

    Args:
        scope: Specifies what part of the app should rerun (Streamlit 1.52+):
            - ``"app"`` (default): Rerun the full app
            - ``"fragment"``: Only rerun the current fragment (must be called inside a fragment)
        wait: Controls the rerun behavior:
            - ``True`` (default): Soft rerun as soon as possible (equivalent to wait=0)
            - ``False``: Hard rerun immediately if possible, bypassing delays
            - ``float``: Wait for specified seconds before rerun (e.g., 1.5)
        debug_msg: Optional debug message to identify who requested the rerun.
            Will be printed when the rerun is triggered.

    Note:
        - Multiple calls to :func:`rerun` during the same execution will merge
          intelligently - the longest total delay will be respected.
        - When ``wait=False``, all pending delayed reruns are cleared and an
          immediate rerun is attempted.
        - When ``scope="fragment"``, the wait parameter is ignored and the fragment
          is rerun immediately, as fragment reruns are typically quick operations.

    Examples:
        Soft rerun as soon as possible::

            rerun()  # Full app rerun

        Fragment-scoped rerun (Streamlit 1.52+ style)::

            @st.fragment
            def my_fragment():
                if st.button("Refresh fragment"):
                    rerun("fragment")  # Positional arg works!

        Ensure toast is visible before rerun::

            st.toast("File saved!", icon="💾")
            rerun(wait=1.5)

        Wait for animation to complete::

            with st.spinner("Processing..."):
                process_data()
            rerun(wait=0.5)  # Let spinner disappear gracefully

        Multiple calls - longest delay wins::

            st.toast("Action 1")
            rerun(wait=1.0)
            st.toast("Action 2")
            rerun(wait=2.0)  # This will execute at 2.0s from now

        Immediate hard rerun (useful in callbacks)::

            st.button("Click me", on_click=lambda: rerun(wait=False))

        Named parameters for clarity::

            rerun(scope="fragment")  # Fragment rerun
            rerun(scope="app", wait=1.5)  # Full app with delay

    See Also:
        :func:`wait`: Request delay without triggering rerun
        :func:`check_rerun`: Execute pending reruns
    """

    # Handle fragment scope: ignore wait and call original directly
    # Fragment reruns are fast and don't need delay management
    if scope == "fragment":
        msg = f"fragment-scoped rerun{f': {debug_msg}' if debug_msg else ''}"
        original_rerun(scope="fragment", debug_msg=msg)
        return

    # Handle wait=False (immediate hard rerun)
    if wait is False:
        # Execute immediately without waiting for current execution
        # This clears any pending delayed reruns and triggers an immediate rerun
        try:
            msg = f"immediate rerun with wait=False{f': {debug_msg}' if debug_msg else ''}"
            original_rerun(debug_msg=msg)  # Trigger immediate rerun (will clear state)
        except Exception:
            # st.rerun() raises an exception when called from within a callback context
            # In this case, fall back to soft rerun with zero delay
            rerun(wait=True, debug_msg=debug_msg)
        return

    # Convert wait to delay value
    if wait is True:
        delay = 0.0
    else:
        delay = float(wait)

    import time
    current_time = time.time()

    # If there's already a pending delay or rerun, merge intelligently
    rerun_request_key = state_key("rerun_request")
    if rerun_request_key in state and state[rerun_request_key]:
        existing = state[rerun_request_key]
        existing_requested_at = existing.get('requested_at', current_time)
        existing_delay = existing.get('delay', 0)

        # Calculate when the existing would execute
        existing_execute_at = existing_requested_at + existing_delay

        # Calculate when this new rerun would execute
        new_execute_at = current_time + delay

        # Use whichever execution time is later (longest total delay)
        if new_execute_at > existing_execute_at:
            # New request requires longer wait - update to new timestamp and delay
            # Merge debug messages if both exist
            existing_msg = existing.get('debug_msg')
            merged_msg = debug_msg
            if existing_msg and debug_msg and existing_msg != debug_msg:
                merged_msg = f"{existing_msg} + {debug_msg}"
            elif existing_msg:
                merged_msg = existing_msg
            state[rerun_request_key] = {
                'requested_at': current_time,
                'delay': delay,
                'requested': True,
                'debug_msg': merged_msg
            }
        else:
            # Existing delay already waits long enough
            # Keep the existing delay but mark as requested
            elapsed = current_time - existing_requested_at
            # Merge debug messages if both exist
            existing_msg = existing.get('debug_msg')
            merged_msg = debug_msg
            if existing_msg and debug_msg and existing_msg != debug_msg:
                merged_msg = f"{existing_msg} + {debug_msg}"
            elif existing_msg:
                merged_msg = existing_msg
            state[rerun_request_key] = {
                'requested_at': current_time,
                'delay': max(0, existing_delay - elapsed),
                'requested': True,
                'debug_msg': merged_msg
            }
    else:
        # First request
        state[rerun_request_key] = {
            'requested_at': current_time,
            'delay': delay,
            'requested': True,
            'debug_msg': debug_msg
        }

def wait(delay: bool | float = True) -> None:
    """Request a minimum delay before any future rerun, without triggering one.

    This function sets a delay requirement that will be honored by any subsequent
    :func:`rerun` call. Unlike :func:`rerun`, this does not trigger a rerun itself.

    Useful when you want to ensure temporal space (e.g., for toasts/animations)
    without causing a rerun yourself.

    Args:
        delay: Controls the delay behavior:
            - ``True`` or ``0`` (default): Does nothing (no additional delay)
            - ``False``: Executes any pending rerun immediately, ignoring previous delays
            - ``float``: Request additional delay (in seconds) before next rerun

    Note:
        Multiple calls to :func:`wait` will use the longest delay.
        The delay is only enforced when :func:`rerun` is eventually called.

    Examples:
        Request delay, someone else will trigger rerun::

            st.toast("Processing complete", icon="✅")
            wait(1.5)  # Ensures toast is visible
            # ... later, someone calls rerun() which will honor the 1.5s delay

        Ensure animation completes::

            st.balloons()
            wait(2.0)  # Balloons get full duration before any rerun

        Execute pending rerun immediately::

            wait(False)  # If a rerun was pending, execute it now

    See Also:
        :func:`rerun`: Trigger a rerun with delay
        :func:`check_rerun`: Execute pending reruns
    """
    # Handle wait(False) - execute pending rerun immediately
    if delay is False:
        rerun_request_key = state_key("rerun_request")
        if rerun_request_key in state and state[rerun_request_key]:
            existing_requested = state[rerun_request_key].get('requested', False)
            if existing_requested:
                # There's a pending rerun - execute it immediately (original_rerun will clear state)
                original_rerun(debug_msg="executing pending rerun immediately from wait(False)")
        return

    # Handle wait(True) or wait(0) - do nothing
    if delay is True or delay == 0:
        return

    # Handle numeric delay
    import time
    current_time = time.time()
    delay = float(delay)

    # Check if there's already a delay or rerun request
    rerun_request_key = state_key("rerun_request")
    if rerun_request_key in state and state[rerun_request_key]:
        existing = state[rerun_request_key]
        existing_requested_at = existing.get('requested_at', current_time)
        existing_delay = existing.get('delay', 0)
        existing_requested = existing.get('requested', False)

        # Calculate when the existing would execute
        existing_execute_at = existing_requested_at + existing_delay

        # Calculate when we want it to execute (at least delay from now)
        desired_execute_at = current_time + delay

        # If our desired delay is longer, update it
        if desired_execute_at > existing_execute_at:
            state[rerun_request_key] = {
                'requested_at': current_time,
                'delay': delay,
                'requested': existing_requested,  # Preserve requested flag
                'debug_msg': existing.get('debug_msg')  # Preserve debug message
            }
        else:
            # Keep existing but update timestamp
            elapsed = current_time - existing_requested_at
            state[rerun_request_key] = {
                'requested_at': current_time,
                'delay': max(0, existing_delay - elapsed),
                'requested': existing_requested,
                'debug_msg': existing.get('debug_msg')  # Preserve debug message
            }
    else:
        # First delay request - create entry with requested=False
        state[rerun_request_key] = {
            'requested_at': current_time,
            'delay': delay,
            'requested': False
        }

def check_rerun() -> None:
    """Check for pending reruns and execute them with delays.

    This function should be placed as the last command in a Streamlit main script.
    It checks for the rerun flag and triggers a rerun if it's set (requested=True),
    waiting for the requested delay if necessary.

    If only :func:`wait` was called (requested=False), no rerun occurs - the delay
    requirement is just stored for any future :func:`rerun` call.

    Note:
        This function is typically called automatically at the end of notebook
        execution. You rarely need to call it manually.

    Examples:
        Typical usage at the end of a Streamlit script::

            # Your Streamlit app code here
            st.config.title("My App")
            # ...

            # Check and execute any pending reruns
            check_rerun()

    See Also:
        :func:`rerun`: Command a rerun with delay
        :func:`wait`: Request delay without rerun
    """
    import time
    rerun_request_key = state_key("rerun_request")
    if rerun_request_key in state and state[rerun_request_key]:
        rerun_info = state[rerun_request_key]
        requested = rerun_info.get('requested', False)

        # Only execute rerun if it was actually requested (not just a delay)
        if requested:
            requested_at = rerun_info.get('requested_at', 0)
            delay_time = rerun_info.get('delay', 0)
            debug_msg = rerun_info.get('debug_msg')

            # Calculate elapsed time since rerun was requested
            elapsed = time.time() - requested_at

            # Wait for remaining delay if needed
            remaining_delay = delay_time - elapsed
            if remaining_delay > 0:
                time.sleep(remaining_delay)

            # Execute rerun (original_rerun will clear the state)
            msg = f"executing scheduled rerun from check_rerun(){f': {debug_msg}' if debug_msg else ''}"
            original_rerun(debug_msg=msg)
        else:
            # If there's a delay request but no rerun request, clear it for next run
            state[rerun_request_key] = None
