from __future__ import annotations

from typing import Any, Optional, Literal
from code_editor import code_editor
from .utils import state, short_id, rerun
import streamlit as st

class editor_output_parser:
    """
    Parses the raw output of the editor widget.

    This class keeps track of output IDs to ensure events are processed only once.
    It returns a pair (event, content) for each call.

    Attributes:
        last_id (str): The ID of the last processed output.
        last_code (str): The last processed code content.

    Methods:
        __call__(output): Process the output and return event and content.
    """
    def __init__(self, editor: Editor) -> None:
        self.last_id: Optional[str] = None
        self.editor = editor

    def __call__(self, output: Optional[dict[str, Any]]) -> Optional[str]:
        if output is None or not output.get('id'):
            event = None
        else:
            if output['id'] != self.last_id:
                self.editor.code.from_ui(output['text'])
                self.last_id = output['id']
                if output.get("type"):
                    event = output["type"]
                else:
                    event = None
            else:
                event = None
        return event

class Code:

    """
    Manages the code content for an Editor/CellUI.

    This class provides methods for getting and setting the code content,
    with mechanisms to handle updates from both the UI and backend.

    Attributes:
        _value (str): The current code content.
        new_code_flag (bool): Flag to indicate if new code has been set from the backend.

    Methods:
        get_value(): Returns the current code content.
        from_ui(value): Updates the code content from the UI.
        from_backend(value): Updates the code content from the backend.
    """

    def __init__(self, value: str = "") -> None:
        self._value = value
        self.new_code_flag = False

    def get_value(self) -> str:
        """
        Returns the current code content.

        Returns:
            str: The current code content stored in the object.
        """
        return self._value

    def from_ui(self, value: str) -> None:
        """
        Updates the code content from the UI.

        Args:
            value (str): The new code content from the UI.

        This method updates the code content while considering the new_code_flag
        to prevent overwriting backend updates with UI input.
        """
        if self.new_code_flag:
            """
            Avoid incoming code from ui to overwrite the code value when it has just been set to a new value by a backend callback
            """
            self.new_code_flag = False
        else:
            self._value = value

    def from_backend(self, value: str) -> None:
        """
        Updates the code content from the backend.

        Args:
            value (str): The new code content from the backend.

        This method updates the code content and sets the new_code_flag to True,
        indicating that the content has been updated by the backend.
        """
        self._value = value
        self.new_code_flag = True

css_string = '''
    background-color: #bee1e5;

    body > #root .ace-streamlit-dark~& {
    background-color: #262830;
    }

    .ace-streamlit-dark~& span {
    color: #fff;
    opacity: 0.6;
    }

    span {
    color: #000;
    opacity: 0.5;
    }

    .code_editor-info.message {
    width: inherit;
    margin-right: 75px;
    order: 2;
    text-align: center;
    opacity: 0;
    transition: opacity 0.7s ease-out;
    }

    .code_editor-info.message.show {
    opacity: 0.6;
    }

    .ace-streamlit-dark~& .code_editor-info.message.show {
    opacity: 0.5;
    }
    '''

class Bar:

    """
    Represents a UI bar in the cell editor.

    This class is used to create info and menu bars for the cell UI.

    Attributes:
        editor (Editor): The parent editor object.
        name (str): The name of the bar.
        order (int): The order of the bar in the UI (1 for top, 3 for bottom).
        info (dict): Additional information for the bar.

    Methods:
        get_info(): Returns the bar's info as a list of dictionaries.
        set_info(info): Sets the bar's info.
        get_dict(): Returns the bar's configuration as a dictionary.
    """

    def __init__(self,editor,name="bar",info=None,order=1):
        self.editor=editor
        self.name=name
        self.order=order
        self.info=info or dict()

    def get_info(self):
        """
        Returns the bar's info as a list of dictionaries.

        Returns:
            list: A list containing a dictionary with the bar's name and style.
        """
        return [dict(
            name=self.info.get("name",""),
            style=self.info.get("style",None)
        )]
    
    def set_info(self,info):
        """
        Sets the bar's info.

        Args:
            info (dict): A dictionary containing the new info for the bar.
        """
        self.info=info


    def get_dict(self):
        """
        Returns the bar's configuration as a dictionary.

        Returns:
            dict: A dictionary containing the complete configuration for the bar,
                  including name, CSS, style, and info.
        """
        if self.order==3:
            border_radius="0px 0px 8px 8px"
        elif self.order==1:
            border_radius="8px 8px 0px 0px"
        else:
            raise ValueError("Bar.order must be 1 or 3")

        info_bar = {
            "name": self.name,
            "css": css_string,
            "style": {
                        "order": f"{self.order}",
                        "display": "flex",
                        "flexDirection": "row",
                        "alignItems": "center",
                        "width": "100%",
                        "height": "2.5rem",
                        "padding": "0rem 0.75rem",
                        "borderRadius": border_radius,
                        "zIndex": "9990"
                    },
            "info": self.get_info()
        }
        return info_bar

class InfoBar(Bar):

    """
    Represents the information bar in the cell UI.

    This class extends the Bar class to create a specialized bar
    for displaying cell information.

    The InfoBar is typically positioned at the bottom of the cell UI.
    """

    def __init__(self,editor,info=None):
        super().__init__(editor,name="info_bar",info=info,order=3)
    
class MenuBar(Bar):

    """
    Represents the menu bar in the cell UI.

    This class extends the Bar class to create a specialized bar
    for cell controls and options.

    The MenuBar is typically positioned at the top of the cell UI.
    """

    def __init__(self,editor,info=None):
        super().__init__(editor,name="menu_bar",info=info,order=1)

class Control:

    """
    Base class for UI controls in the cell editor.

    This class is used to create buttons and toggles for the cell UI.

    Attributes:
        editor (Editor): The parent editor object.
        name (str): The name of the control.
        caption (str): The caption text for the control.
        event (str): The event triggered by the control.
        visible (bool): Whether the control is visible.
        toggled (bool): The toggle state (for toggle controls).
        icons (str|list): The name(s) of the icon(s) to display on the control.
        icon_size (str): The size of the icon
        style (dict): The css styling of the control
        has_caption (bool): Whether to show the control's caption.
        has_icon (bool): Whether to show the control's icon.
        always_on (bool): Whether the button is always shown or only shown when the component has focus
        hover (bool): Whether the control should have a hover effect.
        refresh (bool): Whether the control should trigger a UI refresh

    Methods:
        callback(): The function called when the control is activated.
        get_icon(): Returns the icon for the control.
        get_dict(): Returns the control's configuration as a dictionary.
    """

    def __init__(self,editor,name="control",caption="Click me!",icons="Play",event=None,style=None,callback=None,has_caption=False,has_icon=True,hover=True,always_on=True,icon_size="12px",visible=True,refresh=False):
        self.name=name
        self.editor=editor
        self.caption=caption
        self.has_caption=has_caption
        self.has_icon=has_icon
        self.icon_size=icon_size
        self.hover=hover
        self.always_on=always_on
        self.icons=[icons] if isinstance(icons,str) else icons
        self.type=type
        self.style=style
        self.event=event or short_id()
        self.callback=callback
        self.visible=visible
        self.refresh=refresh
        self.toggled=False
    
    def _callback(self):
        """
        The function called when the control is activated.

        This method is called when the control is interacted with (e.g., clicked).
        It toggles the control's state and calls any custom callback function if defined.
        """
        self.toggled=not self.toggled
        if self.callback:
            self.callback()
        if self.refresh:
            self.editor.refresh()

    def get_icon(self):
        """
        Returns the icon for the control.

        Returns:
            str: The name of the icon to be displayed on the control.
        """
        return self.icons[0]

    def get_dict(self):
        """
        Returns the control's configuration as a dictionary.

        Returns:
            dict: A dictionary containing the complete configuration for the control,
                  including name, icon, style, and event commands.
        """
        style=dict()
        if self.style:
            style.update(self.style)
        button={
            "name": self.caption,
            "feather": self.get_icon(),
            "iconSize":self.icon_size,
            "primary": self.hover,
            "hasText": self.has_caption,
            "alwaysOn": self.always_on,
            "showWithIcon": self.has_icon,
            "commands": [
                ["response",self.event]
            ],
            "style":style
        }
        return button    

class Button(Control):
    """
    Represents a clickable button in the cell UI.

    This class extends the Control class to create a button with
    specific behavior and appearance.

    The button's behavior is defined by its callback method.
    """
    def __init__(self,editor,name="button",caption="Click me!",icon="Play",event=None,style=None,callback=None,has_caption=False,has_icon=True,hover=True,always_on=True,icon_size="12px",visible=True):
        super().__init__(editor,name=name,caption=caption,icons=icon,event=event,style=style,callback=callback,has_caption=has_caption,has_icon=has_icon,hover=hover,always_on=always_on,icon_size=icon_size,visible=visible,refresh=False)
    
class Toggle(Control):
    """
    Represents a toggle switch in the cell UI.

    This class extends the Control class to create a toggle with
    two states (on/off).

    Attributes:
        icons (list): A list of two icon names for the on and off states.
        toggled (bool): The current state of the toggle.

    The toggle's behavior is defined by its callback method, which
    is called whenever the state is changed.
    """
    def __init__(self,editor,name="toggle",caption="Click me!",icons=["Square","CheckSquare"],event=None,style=None,callback=None,has_caption=False,has_icon=True,hover=True,always_on=True,icon_size="12px",visible=True):
        super().__init__(editor,name=name,caption=caption,icons=icons,event=event,style=style,callback=callback,has_caption=has_caption,has_icon=has_icon,hover=hover,always_on=always_on,icon_size=icon_size,visible=visible,refresh=True)

    def get_icon(self):
        return self.icons[1] if self.toggled else self.icons[0]
    
class Editor:

    """
    Manages the UI for a code editor within a cell.

    This class handles the integration of the code editor component
    and associated controls.

    Attributes:
        code (Code): The Code object managing the editor's content.
        buttons (dict): A dictionary of Button and Toggle objects.
        key (str): A unique identifier for the editor.
        info_bar (InfoBar): The information bar for the editor.
        menu_bar (MenuBar): The menu bar for the editor.
        submit_callback (callable): Custom callback for the "submit" event.

    Methods:
        add_button(): Adds a button to the editor UI.
        add_toggle(): Adds a toggle to the editor UI.
        show(): Renders the editor UI.
        refresh(): Triggers a refresh of the editor UI.
        get_params(): Returns the parameters for the code editor component.
        get_output(output): Retrieves the output from the code editor component.
        component(): Renders the code editor component.
        submit(): Handles the submission of editor content.
        process_event(): Processes UI events.
    """

    _excluded=['parser','key','container','code','event','submitted_code','submit_callback','info_bar','menu_bar','kwargs','buttons']

    def __init__(self,code=None,buttons=None,submit_callback=None,key=None,**kwargs):

        if code is None:
            code=Code()
        elif isinstance(code,Code):
            pass
        elif isinstance(code,str):
            code=Code(code)
        else:
            raise TypeError(f"code must be a Code object or a string, got {type(code)}")
        
        self.code=code
        self.event=None
        self.buttons=buttons or dict()
        self.submit_callback=submit_callback
        self.key=key or short_id()
        self.kwargs=kwargs
        self.container=None
        self.info_bar=InfoBar(self)
        self.menu_bar=MenuBar(self)
        self.parser=editor_output_parser(self)    

    def __getattr__(self,attr):
        if attr in self.kwargs:
            return self.kwargs[attr]
        else:
            return super().__getattribute__(attr)
        
    def __setattr__(self,attr,value):
        if attr in self.__class__._excluded:
            super().__setattr__(attr,value)
        else:
            self.kwargs[attr]=value

    @property
    def bindings(self):
        return {button.event:button._callback for button in self.buttons.values()}

    def add_button(self,name="button",caption="Click me!",icon="Play",event=None,style=None,callback=None,has_caption=True,has_icon=True,hover=True,always_on=True,icon_size="12px",visible=True):
        """
        Adds a button to the editor UI.

        Args:
            name (str): The name of the button.
            caption (str): The text to display on the button.
            icon (str): The name of the icon to use.
            event (str): The event identifier for the button.
            style (dict): Custom CSS styles for the button.
            callback (callable): Function to call when the button is clicked.
            has_caption (bool): Whether to show the caption text.
            has_icon (bool): Whether to show the icon.
            hover (bool): Whether to apply hover effects.
            always_on (bool): Whether the button is always visible.
            icon_size (str): The size of the icon.
            visible (bool): Whether the button is visible.
        """
        self.buttons[name]=Button(self,name=name,caption=caption,icon=icon,event=event,style=style,callback=callback,has_caption=has_caption,has_icon=has_icon,hover=hover,always_on=always_on,icon_size=icon_size,visible=visible)

    def add_toggle(self,name="toggle",caption="Toggle me!",icons=["Square","CheckSquare"],event=None,style=None,callback=None,has_caption=True,has_icon=True,hover=True,always_on=True,icon_size="12px",visible=True):
        """
        Adds a toggle to the editor UI.

        Args:
            name (str): The name of the toggle.
            caption (str): The text to display for the toggle.
            icons (list): List of two icon names for off and on states.
            event (str): The event identifier for the toggle.
            style (dict): Custom CSS styles for the toggle.
            callback (callable): Function to call when the toggle state changes.
            has_caption (bool): Whether to show the caption text.
            has_icon (bool): Whether to show the icon.
            hover (bool): Whether to apply hover effects.
            always_on (bool): Whether the toggle is always visible.
            icon_size (str): The size of the icon.
            visible (bool): Whether the toggle is visible.
        """
        self.buttons[name]=Toggle(self,name=name,caption=caption,icons=icons,event=event,style=style,callback=callback,has_caption=has_caption,has_icon=has_icon,hover=hover,always_on=always_on,icon_size=icon_size,visible=visible)

    def get_params(self):
        """
        Returns the parameters for the code editor component.

        Returns:
            dict: A dictionary of parameters used to configure the code editor.
        """
        params=dict(
            lang=self.kwargs.pop('lang','text'),
            key=self.key,
            buttons=[button.get_dict() for button in self.buttons.values() if button.visible],
            options={
                "showLineNumbers":True
            },
            props={ 
                "enableBasicAutocompletion": False, 
                "enableLiveAutocompletion": False, 
                "enableSnippets": False,
                "style":{
                    "borderRadius": "0px 0px 0px 0px"
                }
            }
        )
        params.update(self.kwargs)
        params.update(
            info=self.info_bar.get_dict(),
            menu=self.menu_bar.get_dict()
        )
        return params

    def get_output(self,output):
        """
        Retrieves the output from the code editor component.

        Args:
            output: The raw output from the code editor.

        Returns:
            The retrieved output, either from the session state (if available) or the raw output.
        """
        if self.key in state:
            return state[self.key]
        else:
            return output
            
    def component(self):
        """
        Renders the code editor component.

        This method creates and displays the main code editing interface.
        """
        output=code_editor(self.code.get_value(),**self.get_params())
        event=self.parser(self.get_output(output))
        self.event=event

    def submit(self):
        """
        Handles the submission of editor content.

        This method is called when the editor content is submitted,
        typically triggering the submit_callback if defined.
        """
        if self.submit_callback:
            self.submit_callback()

    def process_event(self):
        """
        Processes UI events.

        This method handles various events triggered by UI interactions,
        such as button clicks or toggles.
        """
        if self.event=="submit":
            self.submit()
        elif self.event in self.bindings:
            self.bindings[self.event]()

    def show(self):
        """
        Renders the editor UI.

        This method is responsible for displaying all components of the editor, and process incoming events from the ui.
        including the code input area and control buttons.
        """
        self.container=st.empty()
        with self.container:
            self.component()
        self.process_event()
    
    def refresh(self):
        """
        Triggers a refresh of the UI.

        This method is used to update the editor's visual representation by requiring a notebook rerun,
        typically after changes to its content or state.
        """
        rerun()
        
class CellUI(Editor):

    """
    Manages the complete UI for a notebook cell.

    This class extends the Editor class to provide cell-specific
    functionality and UI elements.

    Attributes:
        buttons (dict): A dictionary of Button and Toggle objects for cell controls.
        code (Code): The Code object managing the editor's content.
        key (str): A unique identifier for the editor.
        info_bar (InfoBar): The information bar for the editor.
        menu_bar (MenuBar): The menu bar for the editor.
        submit_callback (callable): Custom callback for the "submit" event.

    Methods:
        show(): Renders the cell's UI components.
        component(): Renders the code editor component.
        submit(): Handles the submission of cell content.
        process_event(): Processes UI events.
        refresh(): Triggers a refresh of the cell UI.
    """

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.add_toggle(name="Reactive",caption="Reactive",event="_toggle_reactive",style=dict(top="0px",left="0px",fontSize="14px"),has_caption=True)
        self.add_toggle(name="Fragment",caption="Fragment",event="_toggle_fragment",style=dict(top="0px",left="80px",fontSize="14px"),has_caption=True)
        self.add_button(name="Run",caption="Run",icon="Play",event="run",style=dict(bottom="0px",right="0px",fontSize="14px"),has_caption=False,icon_size="20px")
        #self.add_button(name="Has_run",caption="Has_Run",icon="Check",event="Check",style=dict(bottom="0px",right="30px",fontSize="14px"),has_caption=False,icon_size="20px",hover=False)
        self.add_button(name="Close",caption="Close",icon="X",event="close",style=dict(top="0px",right="0px",fontSize="14px"),has_caption=False,icon_size="20px")
        self.add_button(name="Up",caption="Up",icon="ChevronUp",event="up",style=dict(top="0px",right="60px",fontSize="14px"),has_caption=False,icon_size="20px")
        self.add_button(name="Down",caption="Down",icon="ChevronDown",event="down",style=dict(top="0px",right="30px",fontSize="14px"),has_caption=False,icon_size="20px")
        self.add_button(name="InsertAbove",caption="Insert Above",icon="Plus",event="insert_above",style=dict(top="0px",left="50%",transform="translateX(-50%)",fontSize="14px"),has_caption=False,icon_size="20px")
        self.add_button(name="InsertBelow",caption="Insert Below",icon="Plus",event="insert_below",style=dict(bottom="0px",left="50%",transform="translateX(-50%)",fontSize="14px"),has_caption=False,icon_size="20px")
        # Type switching buttons (next to Cell[i]: info on bottom bar, caption only, no icon)
        self.add_button(name="TypeCode",caption="PY",event="type_code",style=dict(bottom="0px",left="95px",fontSize="12px", transform="translateY(2px)"),has_caption=True,has_icon=False,icon_size="0px")
        self.add_button(name="TypeMarkdown",caption="MD",event="type_markdown",style=dict(bottom="0px",left="120px",fontSize="12px", transform="translateY(2px)"),has_caption=True,has_icon=False,icon_size="0px")
        self.add_button(name="TypeHTML",caption="HTML",event="type_html",style=dict(bottom="0px",left="145px",fontSize="12px", transform="translateY(2px)"),has_caption=True,has_icon=False,icon_size="0px")
    

    