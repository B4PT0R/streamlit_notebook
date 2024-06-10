import re

def format(string, **kwargs):
    """
    formats all occurrences of <<...>> tagged parts found in a string by evaluating the expressions using the kwargs as context namespace
    """
    if not kwargs:
        context = {}
    else:
        context=kwargs
    def replace_expr(match):
        expr = match.group(1)
        try:
            return str(eval(expr, context))
        except Exception as e:
            return '<<' + expr + '>>'
    return re.sub(r'<<(.*?)>>', replace_expr, string)