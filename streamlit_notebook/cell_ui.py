from code_editor import code_editor
import random
import string
from .utils import state
import streamlit as st

def short_id(length=16):
    return ''.join(random.choices(string.ascii_letters, k=length))

class editor_output_parser:
    """
    Class used to parse the raw output of the editor widget.
    Keeps track of outputs ids
    returns a pair (event, content) 
    if a new output is received, event is set to output['type']
    otherwise event is returned as None
    This way we make sure that an event is processed only once
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

    kwargs.update(
        lang=kwargs.get("lang",'text'),
    )

    output=code_editor(*args,**kwargs)
    return output

class Bar:

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

    def __init__(self,editor,info=None):
        super().__init__(editor,name="info_bar",info=info,order=3)
    
class MenuBar(Bar):

    def __init__(self,editor,info=None):
        super().__init__(editor,name="menu_bar",info=info,order=1)

class Control:
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
        self._callback=callback
        self.visible=visible
        self.refresh=refresh
        self.toggled=False
    
    def callback(self):
        self.toggled=not self.toggled
        if self._callback:
            self._callback()
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

    def __init__(self,editor,name="button",caption="Click me!",icon="Play",event=None,style=None,callback=None,has_caption=False,has_icon=True,hover=True,always_on=True,icon_size="12px",visible=True):
        super().__init__(editor,name=name,caption=caption,icons=icon,event=event,style=style,callback=callback,has_caption=has_caption,has_icon=has_icon,hover=hover,always_on=always_on,icon_size=icon_size,visible=visible,refresh=False)
    
class Toggle(Control):

    def __init__(self,editor,name="toggle",caption="Click me!",icons=["Square","CheckSquare"],event=None,style=None,callback=None,has_caption=False,has_icon=True,hover=True,always_on=True,icon_size="12px",visible=True):
        super().__init__(editor,name=name,caption=caption,icons=icons,event=event,style=style,callback=callback,has_caption=has_caption,has_icon=has_icon,hover=hover,always_on=always_on,icon_size=icon_size,visible=visible,refresh=True)

    def get_icon(self):
        return self.icons[1] if self.toggled else self.icons[0]
    
class Editor:

    _excluded=['parser','key','container','code','event','submitted_code','submit_callback','info_bar','menu_bar','kwargs','buttons']

    def __init__(self,code=None,buttons=None,submit_callback=None,key=None,**kwargs):
        self.code=code
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
        return {button.event:button.callback for button in self.buttons.values()}

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
        state.rerun=True
        
class CellUI(Editor):

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.add_toggle(name="Auto_rerun",caption="Auto-rerun",event="toggle_auto_rerun",style=dict(top="0px",left="0px",fontSize="14px"),has_caption=True)
        self.add_toggle(name="Fragment",caption="Run as fragment",event="toggle_fragment",style=dict(top="0px",left="100px",fontSize="14px"),has_caption=True)
        self.add_button(name="Run",caption="Run",icon="Play",event="run",style=dict(bottom="0px",right="0px",fontSize="14px"),has_caption=False,icon_size="20px")
        #self.add_button(name="Has_run",caption="Has_Run",icon="Check",event="Check",style=dict(bottom="0px",right="30px",fontSize="14px"),has_caption=False,icon_size="20px",hover=False)
        self.add_button(name="Close",caption="Close",icon="X",event="close",style=dict(top="0px",right="0px",fontSize="14px"),has_caption=False,icon_size="20px")
        self.add_button(name="Up",caption="Up",icon="ChevronUp",event="up",style=dict(top="0px",right="60px",fontSize="14px"),has_caption=False,icon_size="20px")
        self.add_button(name="Down",caption="Down",icon="ChevronDown",event="down",style=dict(top="0px",right="30px",fontSize="14px"),has_caption=False,icon_size="20px")
    

    