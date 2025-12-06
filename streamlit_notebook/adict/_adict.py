from collections.abc import Mapping
from typing import Optional,Union, Tuple, Set, Dict, List, Any, Callable
from ._typechecker import check_type,TypeMismatchError, coerce
from ._adict_meta import adictMeta, Factory, Computed, AdictItemsView,AdictKeysView,AdictValuesView, AdictConfig
from ._collections_utils import (
    keys,
    set_key, 
    has_key, 
    unroll, 
    join_path, 
    split_path, 
    MISSING, 
    is_container, 
    is_mutable_container, 
    has_nested, 
    get_nested, 
    set_nested, 
    del_nested,
    pop_nested,
    walk,
    unwalk,
    deep_merge, 
    diff_nested, 
    deep_equals,
    exclude,
    extract
)
import copy
import json


class adict(dict, metaclass=adictMeta):
    """
    A dict with additional capabilities.
    (All native dict methods are supported)

    Added features : 
        - attribute-style access.
        - support for recursive conversion of all nested dicts to adicts (including those found in nested mutable containers)
        - extract / exclude methods to conveniently extract selected keys, or exclude unwanted keys
        - type annotations and defaults via class fields
        - robust runtime type-checking and coercion (optional)
        - computed values with caching and dependance bound invalidation
        - rename method to rename keys without changing the values
        - path-pased access for nested structures (has_nested, get_nested, set_nested, del_nested, pop_nested methods)
        - deep walking, merging, diffing, comparing with other nested structures
        - native json support

    Example:
        >>> ad=adict(a=[adict(b=1,c=2)])
        >>> ad.a[0].b
        1
        >>> ad.get_nested("a.0.c")
        2
        >>> ad.set_nested("a.0.d",3)
        >>> ad.walked()
        {"a.0.b":1, "a.0.c":2, "a.0.d":3}
    """

    @classmethod
    def factory(cls,default_factory:Callable):
        """
        Class method to avoid having to import the Factory class separately
        Used to define a factory of default value.
        Instead of passing a static default value to a field, the callable is used to create one for every new instance.

        class user(adict):
            name:str
            id=adict.factory(lambda :random.choice(range(10000)))


        """
        return Factory(default_factory)

    @classmethod
    def config(cls, **kwargs):
        """
        Class method to create an AdictConfig for use in adict subclasses.

        Usage:
            class MyModel(adict):
                _config = adict.config(enforce_json=True, allow_extra=False)
                name: str
                age: int

        Args:
            allow_extra: Allow keys not defined in __fields__
            strict: Enable runtime type checking
            enforce_json: Ensure all values are JSON-serializable
            coerce: Enable automatic type coercion

        Returns:
            AdictConfig instance
        """
        return AdictConfig(**kwargs)

    @classmethod
    def check(cls, field_name):
        """
        Décorateur pour créer des checkers de field.
        
        Args:
            field_name: Le nom du field à checker
        
        Usage:
            @adict.check('email')
            def validate_email(self, value):
                return value.lower().strip()
        """
        def decorator(f):
            f._is_check = True
            f._check_field = field_name
            return f
        return decorator

    @classmethod
    def computed(cls, func=None, *, cache=False, deps=None):
        """
        Create computed properties or decorate methods as computed.
        
        Args:
            func: The function to use for computation
            cache: Whether to cache the computed value
            deps: List of keys to watch for invalidation. Can include:
                  - Regular field names: ['a', 'b'] 
                  - Other computed field names: ['other_computed']
                  - None (default): invalidate on any change
                  - []: never invalidate automatically 
        
        Usage as function:
            sum = adict.computed(lambda ad: ad.a + ad.b, cache=True, deps=['a', 'b'])
            
        Usage as decorator (always with parentheses):
            @adict.computed(cache=True, deps=['a', 'b'])
            def sum_ab(self): return self.a + self.b
            
            @adict.computed(cache=True, deps=['sum_ab', 'c'])  # Dépend d'un autre computed !
            def final_result(self): return self.sum_ab + self.c
            
            @adict.computed(cache=True, deps=[])  # Never invalidate auto
            def expensive_once(self): return heavy_calc()
            
        Cascading invalidation example:
        
        class Calculator(adict):
            a: float = 0
            b: float = 0
            c: float = 0
            
            @adict.computed(cache=True, deps=['a', 'b'])
            def sum_ab(self):
                print("Calculating sum_ab")
                return self.a + self.b
            
            @adict.computed(cache=True, deps=['sum_ab', 'c'])  # Dépend d'un autre computed
            def final_result(self):
                print("Calculating final_result") 
                return self.sum_ab + self.c
                
        calc = Calculator(a=1, b=2, c=3)
        print(calc.final_result)  # "Calculating sum_ab", "Calculating final_result", prints 6
        print(calc.final_result)  # Prints 6 (cached, no calculation)
        
        calc.a = 10  # Change 'a' -> sum_ab invalide -> final_result invalide automatiquement
        print(calc.final_result)  # "Calculating sum_ab", "Calculating final_result", prints 15
        """
        if func is None:
            # Called as decorator: @adict.computed() or @adict.computed(cache=True, deps=['a'])
            def decorator(f):
                f._is_computed = True
                f._computed_cache = cache
                f._computed_deps = deps  # ✅ Ajout : stocker deps sur la fonction
                return f
            return decorator
        else:
            # Called as function: adict.computed(lambda ad: ad.a + ad.b, cache=True, deps=['a', 'b'])
            return Computed(func, cache=cache, deps=deps)

    def __init__(self, *args, **kwargs):

        self._config = type(self)._config.copy()

        super().__init__(*args,**kwargs)

        # Inject defaults and computed
        for key, field in self.__fields__.items():
            value=field.get_default()
            if value is not MISSING:
                if isinstance(value,Computed) or key not in self:
                    dict.__setitem__(self, key, value)

        self.validate()

    def validate(self):
        for key, value in dict.items(self):
            # 1. Clé interdite ? → on coupe court
            if not self._config.allow_extra and key not in self.__fields__:
                raise KeyError(
                    f"Key {key!r} is not allowed. Only the following keys are permitted: "
                    f"{list(self.__fields__.keys())}"
                )

            # 2. On ne valide pas les Computed (leurs valeurs ne sont pas stockées)
            if isinstance(value, Computed):
                continue

            # 3. Validation du contenu
            dict.__setitem__(self, key, self._check_value(key, value))

    def _check_value(self, key, value, hint=None):
        """
        Consolide toute la validation : checkers + type checking.
        Utilisée pour valeurs entrantes, sortantes et computed properties.
        
        Args:
            key: Le nom du field
            value: La valeur à vérifier/transformer  
            hint: Type hint optionnel (si None, pris du Field)
        
        Returns:
            La valeur vérifiée et potentiellement transformée
        """

        # 1. Appliquer les checkers custom d'abord (transformation permissive)
        value = self._apply_checks(key, value)

        # 2. Tenter la coercion
        if self._config.coerce:
            value = self._coerce_value(key, value, hint)
        
        # 3. Type checking ensuite (validation stricte du résultat)
        if hint is None:
            # Récupérer le hint du Field si pas fourni
            field = self.__fields__.get(key)
            if field and field.hint is not None:
                hint = field.hint
        
        # Vérifier le type si on a un hint et que le mode strict est activé
        if hint is not None:
            self._check_type(key, value, hint)

        if self._config.enforce_json:
            self._check_json_serializable(key, value)
        
        return value

    def _apply_checks(self, key, value):
        """Applique tous les checkers d'un field dans l'ordre (parent → enfant)."""
        field = self.__fields__.get(key)
        if field and field.checkers:
            for checker in field.checkers:
                value = checker(self, value)
        return value
    
    def _coerce_value(self, key: str, value: Any, hint: Any = None) -> Any:
        """
        Tentative de coercion de la valeur vers le type attendu.
        """
        if hint is None:
            field = self.__fields__.get(key)
            if field and field.hint is not None:
                hint = field.hint
            else:
                return value  # Pas de hint, pas de coercion
        
        # Si la valeur correspond déjà au type, pas de coercion
        try:
            check_type(hint, value)
            return value
        except:
            pass  # Type check a échoué, on tente la coercion
        
        # Tentative de coercion
        try:
            return coerce(value, hint)
        except:
            return value
    
    def _check_json_serializable(self, key: str, value: Any) -> None:
        """
        Vérifie qu'une valeur est sérialisable en JSON.
        
        Args:
            key: Le nom du field (pour les messages d'erreur)
            value: La valeur à vérifier
            
        Raises:
            ValueError: Si la valeur n'est pas sérialisable en JSON
        """
        try:
            # Test de sérialisation rapide
            json.dumps(value)
        except (TypeError, ValueError, OverflowError) as e:
            # Types problématiques courants
            if isinstance(value, (set, frozenset)):
                suggestion = f" (convert to list: {list(value)!r})"
            elif callable(value):
                suggestion = " (functions are not JSON serializable)"
            elif hasattr(value, '__dict__'):
                suggestion = f" (convert to dict: {vars(value)!r})"
            else:
                suggestion = ""
                
            raise ValueError(
                f"Field '{key}' contains non-JSON-serializable value: {type(value).__name__}{suggestion}"
            ) from e

    def _check_type(self,key,value,hint):
        # basic isinstance check for now
        if self._config.strict:
            try:
                check_type(hint,value)
                return True
            except TypeMismatchError:
                raise TypeError(f"Key {key!r} expected an instance of {hint}, got {type(value)}")
            
    def _invalidate_dependants(self, changed_keys: set):
        """
        Recursively invalidate computed that depend on the given keys.
        Handles cascading dependencies automatically in a single method.
        
        Args:
            changed_keys: Set of keys that have changed (initially the modified key,
                         then computed names that got invalidated)
        """
        if not changed_keys:
            return
            
        newly_invalidated = set()
        
        # Trouver tous les computed qui dépendent des clés modifiées
        for field_name, value in dict.items(self):
            if isinstance(value, Computed):
                if value.should_invalidate_for_keys(changed_keys):
                    if value.cache and value._cache_valid:  # Seulement si effectivement en cache
                        value.invalidate_cache()
                        newly_invalidated.add(field_name)
        
        # Récursion : propager aux computed qui dépendent des computed qu'on vient d'invalider
        if newly_invalidated:
            self._invalidate_dependants(newly_invalidated)

    def _invalidate_all(self):
        for value in dict.values(self):
            if isinstance(value, Computed):
                value.invalidate_cache()

    def _auto_convert_value(self, value):
        if not self._config.auto_convert:
            return value
        # Ici on reste data-structure agnostique
        if is_mutable_container(value):
            # Important : on retourne un adict "pur", pas une sous-classe
            return adict.convert(value)
        return value

    def _auto_convert_and_store(self, key, value):
        new = self._auto_convert_value(value)
        if new is not value:
            # On écrit brut pour ne pas relancer toute la validation
            dict.__setitem__(self, key, new)
            return new
        return value

    # changed dict methods

    def keys(self):
        """Retourne une view des clés (compatibilité dict native)."""
        return AdictKeysView(self)

    def values(self):
        """Retourne une view des valeurs avec validation."""
        return AdictValuesView(self)

    def items(self):
        """Retourne une view des items avec validation."""
        return AdictItemsView(self)

    def __getitem__(self, key):
        value = dict.__getitem__(self, key)

        if isinstance(value, Computed):
            computed_value = value(self)
            checked = self._check_value(key, computed_value)
            # Pour les computed, on NE stocke pas le résultat dans le dict,
            # on fait juste l'auto-convert sur la valeur de retour.
            return self._auto_convert_value(checked)

        # Pour les valeurs stockées : on convertit ET on remplace dans le dict
        return self._auto_convert_and_store(key, value)

    def __setitem__(self, key, value):
        if not self._config.allow_extra and key not in self.__fields__:
            raise KeyError(
                f"Key {key!r} is not allowed. Only the following keys are permitted: "
                f"{list(self.__fields__.keys())}"
            )

        # Cas particulier : on stocke les Computed bruts, sans validation/invalidation
        if isinstance(value, Computed):
            dict.__setitem__(self, key, value)
            return

        # Cas normal : validation / coercion / JSON / type
        value = self._check_value(key, value)
        dict.__setitem__(self, key, value)
        self._invalidate_dependants({key})

    def __delitem__(self, key):
        # On laisse remonter le KeyError si pas de clé
        dict.__delitem__(self, key)
        self._invalidate_dependants({key})

    def __repr__(self):
        content=', '.join(f"{k!r}: {v!r}" for k,v in self.items())
        template=f"{{{content}}}"
        return f"{self.__class__.__name__}({template})"
    
    def __str__(self):
        return repr(self)
        
    def get(self, key, default=None):
        """dict.get() avec validation via __getitem__"""
        try:
            return self[key]  # Force validation
        except KeyError:
            return default
            
    def pop(self, key, default=MISSING):
        """dict.pop() avec validation via __getitem__"""
        try:
            value = self[key]  # Force validation en lecture  
            del self[key]
            return value
        except KeyError:
            if default is not MISSING:
                return default
            raise

    def popitem(self):
        """dict.popitem() avec validation"""
        if not self:
            raise KeyError('popitem(): dictionary is empty')
        key = next(iter(self))
        return key, self.pop(key)  # Utilise notre pop()
        
    def copy(self):
        """Copie avec validation garantie."""
        return type(self)(self)  # Passe par __init__ → validation
        
    @classmethod  
    def fromkeys(cls, iterable, value=None):
        """Crée un adict depuis des clés avec validation."""
        return cls((key, value) for key in iterable)
            
    def __or__(self, other):
        """d1 | d2 - merge operator avec validation (accepte tout Mapping)."""
        if not isinstance(other, Mapping):
            return NotImplemented
        result = self.copy()
        result.update(other)  # update() accepte déjà tout Mapping
        return result

    def __ior__(self, other):
        """d1 |= d2 - in-place merge operator avec validation (accepte tout Mapping)."""
        if not isinstance(other, Mapping):
            return NotImplemented
        self.update(other)  # update() accepte déjà tout Mapping
        return self

    def __reversed__(self):
        """Support pour reversed(d)."""
        return reversed(list(self.keys()))
        
    def setdefault(self, key, default=None):
        """setdefault() avec validation garantie via nos méthodes."""
        if key in self:
            return self[key]
        else:
            self[key] = default 
            return default

    def clear(self):
        dict.clear(self)
        self._invalidate_all()

    # additonal methods

    def __getattr__(self, key):
        """ Permet l'accès aux clés comme attributs."""
        if hasattr(type(self), key):
            return super().__getattribute__(key)
        elif key in self:
            return self[key]
        else:
            return super().__getattribute__(key)

    def __setattr__(self, key, value):
        """ 
        Permet d'affecter une valeur comme un attribut.
        Routing intelligent : attribut existant → protocole Python, nouveau → dict.
        """
        
        if hasattr(type(self), key):
            object.__setattr__(self, key, value)
        else:
            # Nouvelle clé → comportement dict
            self[key] = value

    def __delattr__(self, key):
        """ Permet l'accès aux clés comme attributs. """
        if hasattr(type(self), key):
            object.__delattr__(self, key)
        elif key in self:
            del self[key]
        else:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")

    @classmethod
    def convert(cls, obj:Any, seen: Optional[Dict] = None, root: bool = True) -> 'adict':
        """
        Method used to convert dicts to adicts.
        Takes any obj as input.
        if obj is a dict : we upgrade to adict and continue to the next step
        if obj is a MutableMapping or MutableSequence : we convert the items, and return obj
        else : returns obj directly
        Handles circular references gracefully.
        """
        if seen is None:
            seen = {}  # Map object id -> converted value
            
        obj_id = id(obj)
        if obj_id in seen:
            return seen[obj_id]
            
        # if dict we upgrade to adict first
        if isinstance(obj, dict) and not isinstance(obj,adict):
            if root:
                obj=cls(obj)
            else:
                obj=adict(obj)

        # Register the new instance as output for an already seen input
        seen[obj_id] = obj

        # then we recursively convert the values
        if is_mutable_container(obj):
            # We convert in situ to preserve references of original containers as much as possible
            for k, v in unroll(obj):
                if isinstance(obj, adict):
                    dict.__setitem__(obj, k, cls.convert(v, seen, root=False))
                else:
                    obj[k] = cls.convert(v, seen, root=False)
                    
        return obj


    def to_adict(self):
        """Instance method: Convert the instance in-place and return it."""
        return self.__class__.convert(self)
    
    @classmethod
    def unconvert(cls, obj:Any, seen: Optional[Dict] = None) -> dict:
        """
        Method used to convert adicts to dicts recursively
        Takes any obj as input.
        if obj is an adict : we downgrade to dict and continue to next step
        if obj is a MutableMapping or MutableSequence: We unconvert the items recursively and return obj
        else : returns obj directly
        Handles circular references gracefully.
        """
        if seen is None:
            seen = {}  # Map object id -> unconverted value
            
        obj_id = id(obj)
        if obj_id in seen:
            return seen[obj_id]

        # if adict : we downgrade to dict first   
        if isinstance(obj, adict):
            obj=dict(obj)

        seen[obj_id] = obj

        if is_mutable_container(obj):
            # We unconvert in situ to preserve references of original containers as much as possible
            for k, v in unroll(obj):
                obj[k] = cls.unconvert(v, seen)

        return obj

    def to_dict(self):
        """Instance method: Unconvert the instance in-place and return it."""
        return self.__class__.unconvert(self)

    def get_nested(self, path: str | tuple, default=MISSING):
        """ Accède à une valeur imbriquée via une clé chaînée. """
        return get_nested(self,path,default=default)

    def set_nested(self, path: str | tuple, value):
        """ Affecte une valeur à une clé imbriquée, en créant les niveaux manquants. """
        set_nested(self,path,value)
            
    def del_nested(self, path):
        """Supprime une clé imbriquée."""
        del_nested(self,path)

    def pop_nested(self, path, default=MISSING):
        """Supprime une clé imbriquée."""
        return pop_nested(self,path,default=default)

    def has_nested(self, path: str | tuple):
        """ Vérifie si une clé imbriquée existe. """
        return has_nested(self,path)

    def rename(self, *args, **kwargs):
        """
        Rename keys without altering the values (order is preserved).
        Uses an internal mapping created by dict(*args, **kwargs) where
        the keys represent the old keys and the values represent the new keys.
        Keys not present in the mapping remain unchanged.
        
        Note: If two different keys are renamed to the same new key,
        the last one encountered will overwrite the previous one.
        """
        mapping = dict(*args, **kwargs)
        # Create a new dictionary preserving the order of the original items
        new_dict = type(self)()
        for key, value in self.items():
            new_key = mapping.get(key, key)
            new_dict[new_key] = value
        # Update self in place to maintain the original reference
        self.clear()
        self.update(new_dict)
        
    def exclude(self,*excluded_keys):
        return adict(exclude(self, *excluded_keys)) 
    
    def extract(self,*extracted_keys):
        return adict(extract(self, *extracted_keys)) 

    def walk(self, callback=None, filter=None, excluded=None):
        """ Itère sur les valeurs feuilles avec leur chemin et applique `callback` si fourni. """
        yield from walk(self,callback=callback,filter=filter,excluded=excluded)
    
    def walked(self, callback=None,filter=None):
        """ Retourne un dictionnaire des valeurs feuilles transformées par `callback` si fourni. """
        return adict(self.walk(callback=callback,filter=filter))
    
    @classmethod
    def unwalk(cls,walked):
        unwalked=unwalk(walked)
        if isinstance(unwalked,Mapping):
            return cls(unwalked)
        return unwalked

    def merge(self, other:Mapping):
        """ Fusionne récursivement un autre dictionnaire dans l'instance actuelle. """
        deep_merge(self,other)
    
    def diff(self,other:Mapping):
        return diff_nested(self,other)
    
    def deep_equals(self,other:Mapping):
        return deep_equals(self,other)

    def deepcopy(self) -> "adict":
        return type(self)(copy.deepcopy(dict(self)))
    
    # JSON support
    
    @classmethod
    def loads(cls, s, *, cls_param=None, object_hook=None, parse_float=None,
              parse_int=None, parse_constant=None, object_pairs_hook=None, **kw):
        """Return an adict instance from a JSON string.
        
        This method has the same signature and behavior as json.loads(),
        but returns an adict instance instead of a plain dict.
        
        Args:
            s: JSON string to deserialize
            cls_param: Custom decoder class (usually None)
            object_hook: Function to call with result of every JSON object decoded
            parse_float: Function to call with string of every JSON float to be decoded
            parse_int: Function to call with string of every JSON int to be decoded  
            parse_constant: Function to call with one of: -Infinity, Infinity, NaN
            object_pairs_hook: Function to call with result of every JSON object 
                             decoded with an ordered list of pairs
            **kw: Additional keyword arguments passed to json.loads()
            
        Returns:
            adict: An adict instance containing the parsed JSON data
            
        Raises:
            JSONDecodeError: If the JSON string is invalid
            
        Examples:
            >>> config = AppConfig.loads('{"api_url": "https://api.com", "timeout": 30}')
            >>> config.api_url
            'https://api.com'
        """
        try:
            data = json.loads(s, cls=cls_param, object_hook=object_hook, 
                            parse_float=parse_float, parse_int=parse_int,
                            parse_constant=parse_constant, 
                            object_pairs_hook=object_pairs_hook, **kw)
            return cls(data)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Failed to parse JSON for {cls.__name__}: {e.msg}",
                e.doc, e.pos
            ) from e
    
    @classmethod 
    def load(cls, fp, *, cls_param=None, object_hook=None, parse_float=None,
             parse_int=None, parse_constant=None, object_pairs_hook=None, **kw):
        """Return an adict instance from a JSON file.
        
        This method has the same signature and behavior as json.load(),
        but returns an adict instance instead of a plain dict.
        
        Args:
            fp: File-like object containing JSON document, or path-like object
            cls_param: Custom decoder class (usually None)
            object_hook: Function to call with result of every JSON object decoded
            parse_float: Function to call with string of every JSON float to be decoded
            parse_int: Function to call with string of every JSON int to be decoded
            parse_constant: Function to call with one of: -Infinity, Infinity, NaN
            object_pairs_hook: Function to call with result of every JSON object
                             decoded with an ordered list of pairs  
            **kw: Additional keyword arguments passed to json.load()
            
        Returns:
            adict: An adict instance containing the parsed JSON data
            
        Raises:
            JSONDecodeError: If the JSON is invalid
            FileNotFoundError: If the file doesn't exist
            
        Examples:
            >>> config = AppConfig.load("config.json")
            >>> config = AppConfig.load(open("config.json"))
        """
        # Support path-like objects
        if hasattr(fp, 'read'):
            # File-like object
            try:
                data = json.load(fp, cls=cls_param, object_hook=object_hook,
                               parse_float=parse_float, parse_int=parse_int,
                               parse_constant=parse_constant,
                               object_pairs_hook=object_pairs_hook, **kw)
                return cls(data)
            except json.JSONDecodeError as e:
                raise json.JSONDecodeError(
                    f"Failed to parse JSON for {cls.__name__}: {e.msg}",
                    e.doc, e.pos
                ) from e
        else:
            # Path-like object
            with open(fp, 'r') as f:
                return cls.load(f, cls_param=cls_param, object_hook=object_hook,
                              parse_float=parse_float, parse_int=parse_int,
                              parse_constant=parse_constant,
                              object_pairs_hook=object_pairs_hook, **kw)
    
    def dumps(self, *, skipkeys=False, ensure_ascii=True, check_circular=True,
              allow_nan=True, cls=None, indent=None, separators=None,
              default=None, sort_keys=False, **kw):
        """Return a JSON string representation of the adict.
        
        This method has the same signature and behavior as json.dumps().
        
        Args:
            skipkeys: If True, dict keys that are not basic types will be skipped
            ensure_ascii: If True, non-ASCII characters are escaped  
            check_circular: If False, circular reference check is skipped
            allow_nan: If False, ValueError raised for NaN/Infinity values
            cls: Custom encoder class
            indent: Number of spaces for indentation (None for compact)
            separators: (item_separator, key_separator) tuple  
            default: Function called for objects that aren't serializable
            sort_keys: If True, output of dictionaries sorted by key
            **kw: Additional keyword arguments
            
        Returns:
            str: JSON string representation
            
        Raises:
            TypeError: If the object is not JSON serializable
            ValueError: If allow_nan=False and NaN/Infinity encountered
            
        Examples:
            >>> config.dumps()
            '{"api_url": "https://api.com", "timeout": 30}'
            >>> config.dumps(indent=2, sort_keys=True)
            # Pretty-printed JSON
        """
        return json.dumps(self, skipkeys=skipkeys, ensure_ascii=ensure_ascii,
                         check_circular=check_circular, allow_nan=allow_nan,
                         cls=cls, indent=indent, separators=separators,
                         default=default, sort_keys=sort_keys, **kw)
    
    def dump(self, fp, *, skipkeys=False, ensure_ascii=True, check_circular=True,
             allow_nan=True, cls=None, indent=None, separators=None,
             default=None, sort_keys=False, **kw):
        """Write the adict as JSON to a file.
        
        This method has the same signature and behavior as json.dump().
        
        Args:
            fp: File-like object to write to, or path-like object
            skipkeys: If True, dict keys that are not basic types will be skipped
            ensure_ascii: If True, non-ASCII characters are escaped
            check_circular: If False, circular reference check is skipped  
            allow_nan: If False, ValueError raised for NaN/Infinity values
            cls: Custom encoder class
            indent: Number of spaces for indentation (None for compact)
            separators: (item_separator, key_separator) tuple
            default: Function called for objects that aren't serializable
            sort_keys: If True, output of dictionaries sorted by key
            **kw: Additional keyword arguments
            
        Raises:
            TypeError: If the object is not JSON serializable
            ValueError: If allow_nan=False and NaN/Infinity encountered
            
        Examples:
            >>> config.dump("config.json")
            >>> config.dump(open("config.json", "w"), indent=2)
        """
        # Support path-like objects
        if hasattr(fp, 'write'):
            # File-like object
            json.dump(self, fp, skipkeys=skipkeys, ensure_ascii=ensure_ascii,
                     check_circular=check_circular, allow_nan=allow_nan,
                     cls=cls, indent=indent, separators=separators,
                     default=default, sort_keys=sort_keys, **kw)
        else:
            # Path-like object  
            with open(fp, 'w') as f:
                self.dump(f, skipkeys=skipkeys, ensure_ascii=ensure_ascii,
                         check_circular=check_circular, allow_nan=allow_nan,
                         cls=cls, indent=indent, separators=separators,
                         default=default, sort_keys=sort_keys, **kw)
