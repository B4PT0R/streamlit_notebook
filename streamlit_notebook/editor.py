from code_editor import code_editor

class editor_output_parser:
    """
    Class used to parse the raw output of the editor widget.
    Keeps track of outputs ids
    returns a pair (event, content) 
    if a new output is received, event is set to output['type']
    otherwise event is returned as None
    This way we make sure that an event is processed only once
    """
    def __init__(self):
        self.last_id=None

    def __call__(self,output):
        content=output["text"]
        if 'id' in output and not output['id']==self.last_id:
            self.last_id=output['id']
            if not output["type"]=='':
                event=output["type"]
            else:
                event=None
        else:
            event=None
        return event,content


def editor(*args,**kwargs):
    """
    Custom code editor widget used in cells
    Based on streamlit-code-editor
    """

    # setup the run button
    buttons=[
        {
            "name": "Run",
            "feather": "Play",
            "primary": True,
            "hasText": False,
            "alwaysOn":True,
            "showWithIcon": True,
            "commands": [
                ["response","run"]
            ],
            "style": {
            "bottom": "0.44rem",
            "right": "0.4rem"
            }
        }
    ]

    # default params
    params=dict(
        theme='default',
        buttons=buttons,
        options={
            "showLineNumbers":True
        },
        props={ 
            "enableBasicAutocompletion": False, 
            "enableLiveAutocompletion": False, 
            "enableSnippets": False
        }
    )

    params.update(**kwargs)

    output=code_editor(*args,**params)
    return output
    


