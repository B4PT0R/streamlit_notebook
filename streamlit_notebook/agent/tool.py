
class Tool:
    """
    Tool object used to pass custom tools to the AI.
    """

    def __init__(self,func,name=None,description=None,parameters=None,required=None):
        """
        description: |
            Initializes the Tool object, parsing its docstring YAML for description, parameters, and required fields.
        parameters:
            func:
                description: The function implementing the tool.
            name:
                description: Optional name for the tool (defaults to func.__name__).
            description:
                description: Optional description for the tool (overrides docstring YAML).
            parameters:
                description: Optional parameters schema for the tool (overrides docstring YAML).
            required:
                description: Optional required fields for the tool (overrides docstring YAML).
        """
        self.func=func
        self.name=name or func.__name__
        desc, params, requ = self.parse_doc()
        self.description=description or desc or ''
        self.parameters=parameters or params or {}
        self.required=required or requ or []

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

        doc = self.func.__doc__
        if not doc:
            return '', {}, []

        # Nettoie l'indentation avec dedent, puis strip les quotes et espaces
        doc_str = dedent(doc).strip().strip('"""').strip("'''").strip()

        try:
            data = yaml.safe_load(doc_str)
            # Vérifier que c'est un dict (YAML valide)
            if not isinstance(data, dict):
                # Pas un dict, traiter comme texte simple
                return doc_str, {}, []
        except Exception as e:
            # YAML invalide : retourne tout comme description, ne plante pas
            return doc_str, {}, []

        description = data.get('description', '')
        parameters = data.get('parameters', {})
        required = data.get('required', [])
        return description, parameters, required

    def to_llm_client_format(self):
        """
        description: |
            Converts the Tool object into a function tool schema dictionary suitable for OpenAI function calling.
        returns:
            tool: dict - The dictionary representation of the tool's callable schema.
        """
        properties=dict()
        for name,param in self.parameters.items():
            if isinstance(param,dict):
                # Param est déjà un dict avec type, description, etc.
                properties[name]=param
            elif isinstance(param,str):
                # Param est juste une string description
                properties[name]=dict(type="string", description=param)

        tool=dict(
            type="function",
            function=dict(
                name=self.name,
                description=self.description,
                parameters=dict(
                    type="object",
                    properties=properties
                ),
                required=self.required
            )
        )
        return tool

    def __call__(self,**kwargs):
        """
        description: |
            Calls the wrapped tool function with the given keyword arguments.
        parameters:
            kwargs:
                description: Keyword arguments to pass to the tool function.
        """
        return self.func(**kwargs)