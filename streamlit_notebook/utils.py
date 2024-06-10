import re

def format(string, **kwargs):
    # Si aucun contexte n'est fourni, utiliser un dictionnaire vide
    if not kwargs:
        context = {}
    else:
        context=kwargs
    # Trouver les expressions entre <<...>>
    def replace_expr(match):
        expr = match.group(1)
        try:
            # Évaluer l'expression dans le contexte donné et la convertir en chaîne
            return str(eval(expr, context))
        except Exception as e:
            # print(f"could not evaluate expr: {expr}\n Exception:\n {str(e)}")
            # En cas d'erreur, retourner l'expression non évaluée
            return '<<' + expr + '>>'
    # Remplacer chaque expression par son évaluation
    return re.sub(r'<<(.*?)>>', replace_expr, string)