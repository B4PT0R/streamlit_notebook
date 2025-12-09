from .message import Message
from modict import modict
import json

class Tool:
    """
    Tool object used to pass custom tools to the AI.
    """

    def __init__(self,obj,name=None,description=None,parameters=None,required=None, type=None, mode=None):
        """
        description: |
            Initializes the Tool object, parsing its docstring YAML for description, parameters, and required fields.
        parameters:
            obj:
                description: The object implementing the tool (generally a function).
            name:
                description: Optional name for the tool (defaults to func.__name__).
            description:
                description: Optional description for the tool (overrides docstring YAML).
            parameters:
                description: Optional parameters schema for the tool (overrides docstring YAML).
            required:
                description: Optional required fields for the tool (overrides docstring YAML).
            type:
                description: Optional type for the tool (overrides docstring YAML). 'function' or 'object'
            mode:
                description: Optional mode for the tool (overrides docstring YAML). 'api' or 'parsed'
        """
        self.obj=obj
        self.type=type
        self.name=name or getattr(obj,'__name__',None) or obj.__class__.__name__ 
        self.schema:modict=self.parse_doc()
        if description:
            self.schema.description=description
        if parameters:
            self.schema.parameters=parameters
        if required:
            self.schema.required=required
        self.mode = mode or self.schema.pop('mode', None) or 'api'
        self.type = type or self.schema.pop('type',None) or 'function'

    def __getattr__(self,name):
        return getattr(self.obj,name)

    def __call__(self,**kwargs):
        return self.obj(**kwargs)

    def parse_doc(self):
        """
        description: |
            Parses the YAML docstring of the tool's function to extract description, parameters, and required fields.
        returns:
            description: str - The tool's description.
            parameters: dict - The parameters schema.
            required: list - The required parameter names.
        """
        import yaml
        from textwrap import dedent

        doc = self.obj.__doc__
        if not doc:
            return modict()

        # Nettoie l'indentation avec dedent, puis strip les quotes et espaces
        doc_str = dedent(doc).strip().strip('"""').strip("'''").strip()

        try:
            schema = yaml.safe_load(doc_str)
            # Vérifier que c'est un dict (YAML valide)
            if not isinstance(schema, dict):
                # Pas un dict, traiter comme texte simple
                return modict(description=doc_str)
        except Exception as e:
            # YAML invalide : retourne tout comme description, ne plante pas
            return modict(description=doc_str)

        return modict(schema)

    def to_llm_client_format(self):
        """
        description: |
            Converts the Tool object into a function tool schema dictionary suitable for OpenAI function calling.
        returns:
            tool: dict - The dictionary representation of the tool's callable schema.
        """
        properties=dict()
        for name,param in self.schema.get('parameters',{}).items():
            if isinstance(param,dict):
                # Param est déjà un dict avec type, description, etc.
                properties[name]=dict(param)
            elif isinstance(param,str):
                # Param est juste une string de description
                properties[name]=param

        tool=dict(
            type="function",
            function=dict(
                name=self.name,
                description=self.schema.get('description','No description provided'),
                parameters=dict(
                    type="object",
                    properties=properties
                ),
                required=self.schema.get('required',[])
            )
        )
        return tool
    
    def to_system_message(self):
        """
        description: |
            Converts the Tool object into a system message dictionary suitable for OpenAI chat completions.
        returns:
            message: dict - The dictionary representation of the tool's system message.
        """
        return Message(role="system",content=f"Tool: {self.name}\nSchema:\n{json.dumps(self.to_llm_client_format(), indent=2, ensure_ascii=False)}")