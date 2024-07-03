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
    def __init__(self,initial_code=""):
        self.last_id=None
        self.last_code=initial_code

    def __call__(self,output):
        if output is None:
            event=None
            content=self.last_code
        else:
            content=self.last_code=output['text']
            if not output['id']==self.last_id:
                self.last_code=output['text']
                self.last_id=output['id']
                if not output["type"]=='':
                    event=output["type"]
                else:
                    event=None
            else:
                event=None
        return event,content

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

    def __init__(self,value=""):
        self._value=value
        self.new_code_flag=False

    def get_value(self):
        return self._value
    
    def from_ui(self,value):
        if self.new_code_flag:
            """
            Avoid incoming code from ui to overwrite the code value when it has just been set to a new value by a backend callback
            """
            self.new_code_flag=False
        else:
            self._value=value

    def from_backend(self,value):
        self._value=value
        self.new_code_flag=True

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

def editor(*args,**kwargs):

    """
    Function wrapping the streamlit-code-editor component
    """

    kwargs.update(
        lang=kwargs.get("lang",'text'),
    )

    output=code_editor(*args,**kwargs)
    return output

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
        return [dict(
            name=self.info.get("name",""),
            style=self.info.get("style",None)
        )]
    
    def set_info(self,info):
        self.info=info


    def get_dict(self):
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

    Attributes:
        editor (Editor): The parent editor object.
        info (dict): Additional information to display in the bar.

    The InfoBar is typically positioned at the bottom of the cell UI.
    """

    def __init__(self,editor,info=None):
        super().__init__(editor,name="info_bar",info=info,order=3)
    
class MenuBar(Bar):

    """
    Represents the menu bar in the cell UI.

    This class extends the Bar class to create a specialized bar
    for cell controls and options.

    Attributes:
        editor (Editor): The parent editor object.
        info (dict): Additional information or controls for the menu.

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
        self.toggled=not self.toggled
        if self.callback:
            self.callback()
        if self.refresh:
            self.editor.refresh()

    def get_icon(self):
        return self.icons[0]

    def get_dict(self):
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
        submit_callback (callable): Custom callback for the "submit" event

    Methods:
        add_button(): Adds a button to the editor UI.
        add_toggle(): Adds a toggle to the editor UI.
        show(): Renders the editor UI.
        refresh(): Triggers a refresh of the editor UI.
    """

    _excluded=['parser','key','container','code','event','submitted_code','submit_callback','info_bar','menu_bar','kwargs','buttons']

    def __init__(self,code=None,buttons=None,submit_callback=None,key=None,**kwargs):
        self.code=code or Code()
        self.event=None
        self.buttons=buttons or dict()
        self.submit_callback=submit_callback
        self.key=key or short_id()
        self.kwargs=kwargs
        self.container=None
        self.info_bar=InfoBar(self)
        self.menu_bar=MenuBar(self)
        self.parser=editor_output_parser(self.code.get_value())
        

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
        self.buttons[name]=Button(self,name=name,caption=caption,icon=icon,event=event,style=style,callback=callback,has_caption=has_caption,has_icon=has_icon,hover=hover,always_on=always_on,icon_size=icon_size,visible=visible)

    def add_toggle(self,name="toggle",caption="Toggle me!",icons=["Square","CheckSquare"],event=None,style=None,callback=None,has_caption=True,has_icon=True,hover=True,always_on=True,icon_size="12px",visible=True):
        self.buttons[name]=Toggle(self,name=name,caption=caption,icons=icons,event=event,style=style,callback=callback,has_caption=has_caption,has_icon=has_icon,hover=hover,always_on=always_on,icon_size=icon_size,visible=visible)

    def get_params(self):
        params=dict(
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
            },
            component_props={
                "style":{
                    
                }

            },
            key=self.key
        )
        params.update(self.kwargs)
        params.update(
            info=self.info_bar.get_dict(),
            menu=self.menu_bar.get_dict()
        )
        return params

    def get_output(self,output):
        if self.key in state:
            return state[self.key]
        else:
            return output
            
    def component(self):
        output=editor(self.code.get_value(),**self.get_params())
        event,content=self.parser(self.get_output(output))
        self.code.from_ui(content)
        self.event=event

    def submit(self):
        if self.submit_callback:
            self.submit_callback()

    def process_event(self):
        if self.event=="submit":
            self.submit()
        elif self.event in self.bindings:
            self.bindings[self.event]()

    def show(self):
        self.container=st.empty()
        with self.container:
            self.component()
        self.process_event()
    
    def refresh(self):
        rerun()
        
class CellUI(Editor):

    """
    Manages the complete UI for a notebook cell.

    This class extends the Editor class to provide cell-specific
    functionality and UI elements.
    """

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.add_toggle(name="Auto_rerun",caption="Auto-rerun",event="toggle_auto_rerun",style=dict(top="0px",left="0px",fontSize="14px"),has_caption=True)
        self.add_toggle(name="Fragment",caption="Run as fragment",event="toggle_fragment",style=dict(top="0px",left="100px",fontSize="14px"),has_caption=True)
        self.add_button(name="Run",caption="Run",icon="Play",event="run",style=dict(bottom="0px",right="0px",fontSize="14px"),has_caption=False,icon_size="20px")
        #self.add_button(name="Has_run",caption="Has_Run",icon="Check",event="Check",style=dict(bottom="0px",right="30px",fontSize="14px"),has_caption=False,icon_size="20px",hover=False)
        self.add_button(name="Close",caption="Close",icon="X",event="close",style=dict(top="0px",right="0px",fontSize="14px"),has_caption=False,icon_size="20px")
        self.add_button(name="Up",caption="Up",icon="ChevronUp",event="up",style=dict(top="0px",right="60px",fontSize="14px"),has_caption=False,icon_size="20px")
        self.add_button(name="Down",caption="Down",icon="ChevronDown",event="down",style=dict(top="0px",right="30px",fontSize="14px"),has_caption=False,icon_size="20px")
    

    