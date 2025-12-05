from collections.abc import ValuesView, ItemsView, KeysView
from typing import  Optional,Union,Tuple, Set, Dict, List, Any, Type, Callable
from types import FunctionType
from ._collections_utils import MISSING


class AdictKeysView(KeysView):
    def __init__(self, mapping):
        self._mapping = mapping
    
    def __len__(self):
        return len(self._mapping)
    
    def __contains__(self, key):
        return key in self._mapping
    
    def __iter__(self):
        return iter(self._mapping)

class AdictValuesView(ValuesView):
    def __init__(self, mapping):
        self._mapping = mapping
    
    def __len__(self):
        return len(self._mapping)
    
    def __contains__(self, value):
        for key in self._mapping:
            if self._mapping[key] == value:  # Validation via __getitem__
                return True
        return False
    
    def __iter__(self):
        for key in self._mapping:
            yield self._mapping[key]  # Validation via __getitem__

class AdictItemsView(ItemsView):
    def __init__(self, mapping):
        self._mapping = mapping
    
    def __len__(self):
        return len(self._mapping)
    
    def __contains__(self, item):
        key, value = item
        try:
            return self._mapping[key] == value  # Validation via __getitem__
        except KeyError:
            return False
    
    def __iter__(self):
        for key in self._mapping:
            yield (key, self._mapping[key])  # Validation via __getitem__

class Factory:

    def __init__(self,factory:Callable):
        self.factory=factory

    def __call__(self):
        return self.factory()
    
class Check:
    """
    Représente un checker qui valide/transforme une valeur de field.
    
    Args:
        func: Une fonction qui prend (instance, value) et retourne la valeur transformée
        field_name: Le nom du field à checker
    """
    
    def __init__(self, func: Callable, field_name: str):
        self.func = func
        self.field_name = field_name

    def __call__(self, instance, value):
        """Execute le checker sur la valeur."""
        try:
            return self.func(instance, value)
        except Exception as e:
            raise ValueError(f"Error in checker for field '{self.field_name}': {e}")

class Computed:
    """
    Represents a computed property that dynamically calculates its value.
    
    Args:
        func: A callable that takes the adict instance and returns the computed value
        cache: Whether to cache the computed value (default: False)
        deps: List of keys to watch for cache invalidation. If None, cache is invalidated
              on any change. If empty list [], cache is never invalidated automatically.
    """
    
    def __init__(self, func: Callable, cache: bool = False, deps: Optional[List[str]] = None):
        self.func = func
        self.cache = cache
        # Si deps pas fourni explicitement, le récupérer de la fonction décorée
        if deps is None and hasattr(func, '_computed_deps'):
            deps = func._computed_deps
        self.deps = deps  # None = invalider sur tout changement, [] = jamais invalider auto
        self._cached_value = MISSING
        self._cache_valid = False

    def copy(self):
        return Computed(self.func,self.cache,deps=self.deps)

    def __call__(self, instance):
        """Compute the value for the given adict instance."""
        if self.cache and self._cache_valid:
            return self._cached_value
            
        try:
            value = self.func(instance)
            if self.cache:
                self._cached_value = value
                self._cache_valid = True
            return value
        except Exception as e:
            raise ValueError(f"Error computing value: {e}")
    
    def invalidate_cache(self):
        """Invalidate the cached value."""
        self._cache_valid = False
        self._cached_value = MISSING

    def should_invalidate_for_keys(self, keys: set) -> bool:
        """
        Check if this computed should be invalidated when any of the given keys change.
        
        Args:
            keys: Set of keys that have changed
            
        Returns:
            bool: True if cache should be invalidated
        """
        if not self.cache:
            return False  # Pas de cache = pas d'invalidation
            
        if self.deps is None:
            return True  # None = invalider sur tout changement
            
        if len(self.deps) == 0:
            return False  # Liste vide = jamais invalider automatiquement
            
        # Invalider si au moins une dépendance est dans les clés modifiées
        return bool(set(self.deps) & keys)

class Field:
    def __init__(self, hint=None, default=MISSING, checkers=None):
        self.default = default
        self.hint = hint
        self.checkers = checkers or []  # Liste des Check objects

    def add_checker(self, checker):
        """Ajoute un checker à la liste."""
        self.checkers.append(checker)

    def get_default(self):
        if isinstance(self.default, Factory):
            value=self.default()
        else:
            value=self.default
        if isinstance(value,Computed):
            value=value.copy()
        return value

def is_locally_defined_class(key: str, value: Any, name: str, dct: Dict[str, Any]) -> bool:
    """Détermine si une classe a été définie dans ce namespace"""
    if not isinstance(value, type):
        return False
    
    # Même logique que pour les fonctions
    expected_qualname = f"{name}.{key}"
    return (value.__module__ == dct['__module__'] and
            value.__qualname__ == expected_qualname)

def is_locally_defined_descriptor(key: str, value: Any, name: str, dct: Dict[str, Any]) -> bool:
    """Détermine si un descripteur a été défini dans cette classe vs assigné"""
    
    # Extraire la fonction sous-jacente selon le type
    if isinstance(value, FunctionType):
        underlying_func = value
    elif isinstance(value, (classmethod, staticmethod)):
        underlying_func = value.__func__
    elif isinstance(value, property):
        underlying_func = value.fget
    else:
        return False  # Autres descripteurs → assignés par défaut
    
    # Vérifier si défini localement via qualname
    expected_qualname = f"{name}.{key}"
    return (underlying_func.__module__ == dct['__module__'] and
            underlying_func.__qualname__ == expected_qualname)

def is_field(key: str, value: Any, name: str, bases: Tuple[Type, ...], dct: Dict[str, Any]) -> bool:
    # Already a Field
    if isinstance(value, Field):
        return True
    
    # @adict.computed() decorated functions are always fields
    if hasattr(value, '_is_computed'):
        return True
    
    # @adict.check() decorated functions are NOT fields - traitement spécial
    if hasattr(value, '_is_check'):
        return False
    
    # Skip private/special attributes
    if key.startswith('__'):
        return False
    
    # Exclude attrs already present in the hierarchy
    for base in bases:
        if hasattr(base, key):
            return False
        
    # check classes
    if isinstance(value, type):
        return not is_locally_defined_class(key, value, name, dct)
       
    # check descriptors
    if hasattr(value, '__get__') or isinstance(value, (classmethod, staticmethod, property)):
        return not is_locally_defined_descriptor(key, value, name, dct)
                   
    return True


class adictMeta(type):

    def __new__(mcls, name, bases, dct):
        fields = {}
        annotations = dct.get('__annotations__', {})

        # Merge with fields from parent classes respecting mro order
        for base in reversed(bases):
            if hasattr(base,'__fields__'):
                fields.update(base.__fields__)

        # deal with annotations
        for key, hint in annotations.items():
            if key in dct:
                value = dct[key]
                if isinstance(value, FunctionType) and hasattr(value, '_is_computed'):
                    # @adict.computed() decorated method
                    cache = getattr(value, '_computed_cache', False)
                    computed_obj = Computed(value, cache=cache)
                    # Utiliser l'annotation de retour de la fonction si disponible
                    func_return_hint = getattr(value, '__annotations__', {}).get('return')
                    final_hint = func_return_hint if func_return_hint is not None else hint
                    fields[key] = Field(default=computed_obj, hint=final_hint)
                elif not isinstance(value, Field):
                    fields[key] = Field(default=value, hint=hint)
                else:
                    # already a field, we add the hint (unless already defined)
                    if value.hint is None:
                        value.hint = hint
                    fields[key] = value
                dct.pop(key)
            else:
                # Annotation without value -> Field(default=MISSING)
                fields[key] = Field(default=MISSING, hint=hint)
        
        # deal with namespace
        for key, value in list(dct.items()):
            if key not in annotations:
                if is_field(key, value, name, bases, dct):
                    if isinstance(value, FunctionType) and hasattr(value, '_is_computed'):
                        # @adict.computed() decorated method
                        cache = getattr(value, '_computed_cache', False)
                        computed_obj = Computed(value, cache=cache)
                        # Utiliser l'annotation de retour de la fonction si disponible
                        func_return_hint = getattr(value, '__annotations__', {}).get('return')
                        final_hint = func_return_hint if func_return_hint is not None else None
                        fields[key] = Field(default=computed_obj, hint=final_hint)
                    elif not isinstance(value, Field):
                        fields[key] = Field(default=value)
                    else:
                        fields[key] = value
                    dct.pop(key)

        # Traitement des checkers
        for key, value in list(dct.items()):
            if isinstance(value, FunctionType) and hasattr(value, '_is_check'):
                field_name = value._check_field
                check_obj = Check(value, field_name)
                
                # Field existe déjà (hérité ou déclaré dans cette classe) ?
                if field_name in fields:
                    fields[field_name].add_checker(check_obj)
                else:
                    # Créer un nouveau Field minimal pour le checker
                    fields[field_name] = Field(checkers=[check_obj])
                
                # Retirer la fonction du namespace de la classe
                dct.pop(key)

        # Store fields in __fields__
        dct['__fields__'] = fields

        # _allow_extra
        if '_allow_extra' not in dct:
            dct['_allow_extra'] = True

        # _strict pour toggle le runtime type checking
        if '_strict' not in dct:
            dct['_strict'] = False

        if '_enforce_json' not in dct:
            dct['_enforce_json'] = False

        if '_coerce' not in dct:
            dct['_coerce'] = False

        return super().__new__(mcls, name, bases, dct)