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
    
def rel_pos(x):
    return str(x)+'%'

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

class InfoBar:

    def __init__(self,editor,info=None):
        self.editor=editor
        self.info=info or dict()

    def get_info(self):
        return [dict(
            name=self.info.get("name",""),
            style=self.info.get("style",None)
        )]
    
    def set_info(self,info):
        self.info=info


    def get_dict(self):
        info_bar = {
            "name": "language info",
            "css": css_string,
            "style": {
                        "order": "3",
                        "display": "flex",
                        "flexDirection": "row",
                        "alignItems": "center",
                        "width": "100%",
                        "height": "2.5rem",
                        "padding": "0rem 0.75rem",
                        "borderRadius": "0px 0px 8px 8px",
                        "zIndex": "9990"
                    },
            "info": self.get_info()
        }
        return info_bar
    
class MenuBar:

    def __init__(self,editor,info=None):
        self.editor=editor
        self.info=info or dict()

    def get_info(self):
        return [dict(
            name=self.info.get("name",""),
            style=self.info.get("style",None)
        )]
    
    def set_info(self,info):
        self.info=info


    def get_dict(self):
        menu_bar = {
            "name": "language info",
            "css": css_string,
            "style": {
                        "order": "1",
                        "display": "flex",
                        "flexDirection": "row",
                        "alignItems": "center",
                        "width": "100%",
                        "height": "2.5rem",
                        "padding": "0rem 0.75rem",
                        "borderRadius": "8px 8px 0px 0px",
                        "zIndex": "9990"
                    },
            "info": self.get_info()
        }
        return menu_bar

class Button:

    def __init__(self,editor,name="button",caption="Click me!",icon="Play",style=None,callback=None,has_caption=False,has_icon=True,hover=True,always_on=True,icon_size="12px",visible=True):
        self.name=name
        self.editor=editor
        self.caption=caption
        self.has_caption=has_caption
        self.has_icon=has_icon
        self.icon_size=icon_size
        self.hover=hover
        self.always_on=always_on
        self.icon=icon
        self.type=type
        self.style=style
        self.event=short_id()
        self._callback=callback
        self.visible=visible
    
    def callback(self):
        if self._callback:
            self._callback()

    def get_dict(self):
        style=dict()
        if self.style:
            style.update(self.style)
        button={
            "name": self.caption,
            "feather": self.icon,
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
    
class Toggle:

    def __init__(self,editor,name="toggle",caption="toggle",icons=["Square","CheckSquare"],style=None,callback=None,has_caption=False,has_icon=True,hover=True,always_on=True,icon_size="12px",visible=True):
        self.name=name
        self.editor=editor
        self.caption=caption
        self.has_caption=has_caption
        self.has_icon=has_icon
        self.icon_size=icon_size
        self.hover=hover
        self.always_on=always_on
        self.icons=icons
        self.toggled=False
        self.type=type
        self.style=style
        self.event=short_id()
        self._callback=callback
        self.visible=visible
    
    def callback(self):
        self.toggled=not self.toggled
        if self._callback:
            self._callback()
        self.editor.refresh()

    def get_dict(self):
        style=dict()
        if self.style:
            style.update(self.style)
        button={
            "name": self.caption,
            "feather": self.icons[1] if self.toggled else self.icons[0],
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

class Editor:

    _excluded=['parser','key','container','code','event','submitted_code','submit_callback','info_bar','menu_bar','kwargs','buttons']

    def __init__(self,**kwargs):
        self.code=kwargs.pop('code',"")
        self.event=None
        self.buttons=kwargs.pop('buttons',{})
        self.submit_callback=kwargs.pop('submit_callback',None)
        self.key=kwargs.pop('key',short_id())
        self.kwargs=kwargs
        self.container=None
        self.info_bar=InfoBar(self)
        self.menu_bar=MenuBar(self)
        self.parser=editor_output_parser(self.code)
        

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

    def add_button(self,name="button",caption="Click me!",icon="Play",style=None,callback=None,has_caption=True,has_icon=True,hover=True,always_on=True,icon_size="12px",visible=True):
        self.buttons[name]=Button(self,name=name,caption=caption,icon=icon,style=style,callback=callback,has_caption=has_caption,has_icon=has_icon,hover=hover,always_on=always_on,icon_size=icon_size,visible=visible)

    def add_toggle(self,name="toggle",caption="Toggle me!",icons=["Square","CheckSquare"],style=None,callback=None,has_caption=True,has_icon=True,hover=True,always_on=True,icon_size="12px",visible=True):
        self.buttons[name]=Toggle(self,name=name,caption=caption,icons=icons,style=style,callback=callback,has_caption=has_caption,has_icon=has_icon,hover=hover,always_on=always_on,icon_size=icon_size,visible=visible)

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
            return None
            

    def component(self):
        output=editor(self.code,**self.get_params())
        event,content=self.parser(self.get_output(output))
        self.code=content
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
        st.rerun()
        
        



class CellUI(Editor):

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.add_toggle(name="Auto_rerun",caption="Auto-rerun",style=dict(top="0px",left="0px",fontSize="14px"),has_caption=True)
        self.add_toggle(name="Fragment",caption="Run as fragment",style=dict(top="0px",left="100px",fontSize="14px"),has_caption=True)
        self.add_button(name="Run",caption="Run",icon="Play",style=dict(bottom="0px",right="0px",fontSize="14px"),has_caption=False,icon_size="20px")
        self.add_button(name="Close",caption="Close",icon="X",style=dict(top="0px",right="0px",fontSize="14px"),has_caption=False,icon_size="20px")
        self.add_button(name="Up",caption="Up",icon="ChevronUp",style=dict(top="0px",right="60px",fontSize="14px"),has_caption=False,icon_size="20px")
        self.add_button(name="Down",caption="Down",icon="ChevronDown",style=dict(top="0px",right="30px",fontSize="14px"),has_caption=False,icon_size="20px")
    

    