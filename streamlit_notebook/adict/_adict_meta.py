from collections.abc import ValuesView, ItemsView, KeysView
from typing import  Optional,Union,Tuple, Set, Dict, List, Any, Type, Callable
from types import FunctionType
from ._collections_utils import MISSING
from dataclasses import dataclass, field, fields, MISSING as DC_MISSING
from typing import FrozenSet


@dataclass(frozen=True)
class AdictConfig:
    allow_extra: bool = True
    strict: bool = False
    enforce_json: bool = False
    coerce: bool = False

    # champs passés explicitement à __init__
    _explicit: FrozenSet[str] = field(default_factory=frozenset,init=False,repr=False)

    def __init__(self, **kwargs):
        # 1) garder la liste des clés explicitement fournies
        object.__setattr__(self, "_explicit", frozenset(kwargs.keys()))

        # 2) appliquer kwargs ou defaults de classe
        for f in fields(self):
            if not f.init or f.name == "_explicit":
                continue

            if f.name in kwargs:
                value = kwargs[f.name]
            else:
                if f.default is not DC_MISSING:
                    value = f.default
                elif f.default_factory is not DC_MISSING:  # type: ignore[attr-defined]
                    value = f.default_factory()         # type: ignore[misc]
                else:
                    raise TypeError(f"Missing required field {f.name!r}")

            object.__setattr__(self, f.name, value)

    @classmethod
    def _from_values(cls, values: dict[str, object], explicit: FrozenSet[str]) -> "AdictConfig":
        """
        Constructeur interne qui contourne __init__ pour
        contrôler à la fois les valeurs et _explicit.
        """
        self = object.__new__(cls)  # n'appelle pas __init__
        for f in fields(cls):
            if f.name == "_explicit":
                continue
            object.__setattr__(self, f.name, values[f.name])
        object.__setattr__(self, "_explicit", explicit)
        return self

    def merge(self, other: "AdictConfig") -> "AdictConfig":
        """
        Comme dict.update :
        - les champs explicitement définis dans `other` écrasent ceux de `self`
        - les autres restent ceux de `self`
        - _explicit du résultat = union des explicites de self et other
        """
        merged_values: dict[str, object] = {}

        for f in fields(self):
            if not f.init or f.name == "_explicit":
                continue

            name = f.name
            if name in other._explicit:
                merged_values[name] = getattr(other, name)
            else:
                merged_values[name] = getattr(self, name)

        merged_explicit = self._explicit | other._explicit

        return AdictConfig._from_values(merged_values, merged_explicit)


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

        # Setup _config using AdictConfig with proper MRO merging

        # Construire une config parent à partir de TOUTES les bases
        parent_config = None

        # On parcourt les bases de la dernière à la première
        # pour que la base la plus à gauche (dans class X(A, B)) gagne
        for base in reversed(bases):
            base_conf = getattr(base, '_config', None)
            if base_conf is None:
                continue

            if parent_config is None:
                parent_config = base_conf
            else:
                # merge comme dict.update : les champs explicites de base_conf
                # écrasent ceux déjà dans parent_config
                parent_config = parent_config.merge(base_conf)

        if '_config' in dct:
            # _config explicitement défini dans cette classe
            local_config = dct['_config']
            if not isinstance(local_config, AdictConfig):
                raise TypeError(
                    f"_config must be an AdictConfig instance created via adict.config(), "
                    f"got {type(local_config)}. Use: _config = adict.config(enforce_json=True, ...)"
                )

            if parent_config is not None:
                # On empile la config locale par-dessus la config combinée des bases
                effective_config = parent_config.merge(local_config)
            else:
                # Pas de parents qui ont une config → on prend juste la locale
                effective_config = local_config
        else:
            # Pas de _config local → héritage pur ou defaults
            if parent_config is not None:
                effective_config = parent_config
            else:
                effective_config = AdictConfig()

        dct['_config'] = effective_config

        return super().__new__(mcls, name, bases, dct)