"""Collections utilities for nested data structures.

This module provides a comprehensive set of tools for working with nested data structures
in Python, particularly focusing on Mappings (like dictionaries) and Sequences (like lists).
It enables deep traversal, comparison, merging, and manipulation of nested structures
while maintaining type safety and providing clear error handling.

Key Features:
    - Path-based access: Access nested values using string paths ("a.b.0.c") or key tuples
    - Deep operations: Compare, merge, and modify nested structures
    - Type-safe: Comprehensive type hints and runtime type checking
    - Container views: Create custom views over container data
    - Structure traversal: Walk through nested structures with custom callbacks and filters

Main Components:
    - View: Base class for creating custom container views
    - MISSING: Sentinel value for distinguishing missing values from None
    - Container operations: get_nested(), set_nested(), del_nested(), has_nested()
    - Deep operations: deep_merge(), deep_equals(), diff_nested()
    - Traversal: walk(), walked() for recursive container traversal
    
Typical Usage:
    >>> from collections_utils import get_nested, set_nested, walk
    
    # Access nested values with string paths
    >>> data = {"users": [{"name": "Alice", "age": 30}]}
    >>> get_nested(data, "users.0.name")
    'Alice'
    
    # Modify nested structures
    >>> set_nested(data, "users.0.email", "alice@example.com")
    >>> data
    {"users": [{"name": "Alice", "age": 30, "email": "alice@example.com"}]}
    
    # Walk through nested structures
    >>> for path, value in walk(data):
    ...     print(f"{path}: {value}")
    users.0.name: Alice
    users.0.age: 30
    users.0.email: alice@example.com

Type Definitions:
    - Key: Union[int, str] - Valid container keys/indices
    - Path: Union[str, Tuple[Key, ...]] - Path to nested values
    - Container: Union[Mapping, Sequence] - Any container type
    - MutableContainer: Union[MutableMapping, MutableSequence] - Mutable containers

Notes:
    - String paths use dots as separators: "a.0.b"
    - Numeric path components are converted to integers: "users.0" -> ("users", 0)
    - Container operations maintain the original container types
    - The MISSING sentinel distinguishes missing values from None values
"""

from collections.abc import Collection,Mapping,Sequence,MutableMapping,MutableSequence
from typing import Any, Union, Dict, TypeVar, Tuple, Type, Optional, Set, Callable, TypeAlias, Generic, Iterator
from itertools import islice

# Type definitions for improved clarity and type safety
Key: TypeAlias = Union[int, str]  # Valid key types for containers
Path: TypeAlias = Union[str, Tuple[Key, ...]]  # Path can be string ("a.b.c") or tuple of keys
Container: TypeAlias = Union[Mapping, Sequence]  # Any immutable container
MutableContainer: TypeAlias = Union[MutableMapping, MutableSequence]  # Any mutable container
T = TypeVar('T')  # Generic type for values
C = TypeVar('C', bound=Container)  # Generic type constrained to Containers
MC = TypeVar('MC', bound=MutableContainer)  # Generic type for mutable containers
CallbackFn = Callable[[Any], Any]  # Type for callback functions
FilterFn = Callable[[str, Any], bool]  # Type for filter predicates

class _MISSING:
    """Sentinel class representing a missing value.
    
    Used instead of None when None is a valid value. This helps distinguish
    between "no value set" and "value explicitly set to None".
    """
    def __str__(self)->str:
        return "MISSING"
    
    def __repr__(self)->str:
        return "MISSING"
    
    def __bool__(self)->bool:
        return False

# Sentinel instance
MISSING=_MISSING()

class View(Collection[T], Generic[C, T]):

    """Base View class for creating custom views over any Mapping or Sequence.
    
    Provides a read-only view over container data with custom element access logic.
    Subclasses must implement _get_element(key) to determine how elements are accessed.
    
    Type Parameters:
        C: The container type (must be Mapping or Sequence)
        T: The type of elements in the view
    
    Args:
        data: The container to create a view over
        
    Raises:
        TypeError: If data is not a Mapping or Sequence
        
    Examples:
        >>> class Keys(View[Mapping, Key]):
        ...     def _get_element(self, key: Key) -> Key:
        ...         return key
        >>> class Values(View[Mapping, T]):
        ...     def _get_element(self, key: Key) -> T:
        ...         return self.data[key]
    """

    def __init__(self, data:C) -> None:
        if not isinstance(data,(Mapping,Sequence)):
            raise TypeError(f"The data on which a View is defined is expected to be a Mapping or Sequence. Got {type(data)}")
        self._data:C = data
        self._nmax: int = 10 # max number of elements to show in repr

    @property
    def data(self) -> C:
        return self._data

    def _get_element(self,key:Key) -> T:
        """Takes a key and returns the corresponding view element"""
        raise NotImplementedError()
    
    def __iter__(self) -> Iterator[T]:
        """Return an iterator over view elements"""
        return iter(self._get_element(key) for key in keys(self.data))
    
    def __len__(self) -> int:
        """Return the number of elements in the view."""
        return len(self.data)
    
    def __repr__(self) -> str:
        """String representation of the view"""
        content=', '.join(repr(self._get_element(key)) for key in islice(keys(self.data),self._nmax))
        if len(self.data)>self._nmax:
            content+=", ..."
        return f"{self.__class__.__name__}({content})"

    def __contains__(self, item:Any) -> bool:
        """Check if an element is in the view."""
        return any(item==self._get_element(key) for key in keys(self.data))

def join_path(path_tuple:Tuple[Key,...])-> str:
    """
    joins a path tuple into a path str : ('a',0,'b') -> "a.0.b"
    """
    return '.'.join(str(k) for k in path_tuple)

def split_path(path_str:str)-> Tuple[Key,...]:
    """
    splits a path str into a path tuple : "a.0.b" -> ('a',0,'b') 
    """
    def format(key:str)-> Key:
        try:
            return int(key)
        except ValueError:
            return key
    return tuple(format(k) for k in path_str.split('.'))

def keys(obj:Container)-> Iterator[Key]:
    """Yield possible keys or indices of a container.
    
    Args:
        obj: Mapping or Sequence to get keys from
        
    Yields:
        Keys for Mapping, indices for Sequence
        
    Raises:
        TypeError: If obj is neither Mapping nor Sequence
    """
    if isinstance(obj,Mapping):
        yield from obj.keys()
    elif isinstance(obj,Sequence):
        yield from range(len(obj))
    else:
        raise TypeError(f"Expected a Mapping or Sequence container, got {type(obj)}")
    
def has_key(obj:Container,key:Key)->bool:
    """Check if a key/index exists in a container.
    
    Args:
        obj: Container to check
        key: Key (for Mapping) or index (for Sequence) to look for
        
    Returns:
        True if key exists, False otherwise
        
    Raises:
        TypeError: If obj is neither Mapping nor Sequence
    """        
    if isinstance(obj,Mapping):
        return key in obj
    elif isinstance(obj,Sequence):
        return isinstance(key,int) and 0<=key<len(obj)
    else:
        raise TypeError(f"Expected a Mapping or Sequence container, got {type(obj)}")

def set_key(obj:MutableContainer,key:Key,value:Any):
    if not is_mutable_container(obj):
        raise TypeError(f"Expected a MutableMapping or MutableSequence container. Got {type(obj)}")
    if isinstance(obj,MutableMapping):
        obj[key]=value
    elif isinstance(obj,MutableSequence):
        if isinstance(key,int):
            while len(obj)<=key:
                obj.append(MISSING)
            obj[key]=value
        else:
            raise IndexError(f"Invalid key type. Expected int, got {type(key)}")

def is_container(obj:Any, excluded:Optional[Tuple[Type,...]]=None)->bool:
    """Test if an object is a container (but not an excluded type).
    
    Args:
        obj: Object to test
        excluded: Types to not consider as containers (default: str, bytes, bytearray)
        
    Returns:
        True if obj is a non-excluded container
    """
    excluded= excluded if excluded is not None else (str,bytes,bytearray)
    return (isinstance(obj,Mapping) or isinstance(obj,Sequence)) and not isinstance(obj,excluded)

def is_mutable_container(obj:Any)->bool:
    """Test if an object is a mutable container.
    
    Args:
        obj: Object to test
        
    Returns:
        True if obj is MutableMapping or MutableSequence
    """
    return isinstance(obj,MutableMapping) or isinstance(obj,MutableSequence)

def unroll(obj: Container) -> Iterator[Tuple[Key, Any]]:
    """Yield (key, value) pairs from a container.
    
    Args:
        obj: Container to unroll
        
    Yields:
        Tuple of (key, value) for each element
        
    Raises:
        TypeError: If obj is not a container
    """
    if not is_container(obj):
        raise TypeError(f"Expected a Mapping or Sequence container, got {type(obj)}")
    for key in keys(obj):
        yield key,obj[key]
        

def get_nested(obj: Container, path: Path, default: Any = MISSING) -> Any:
    """Retrieve a nested value using a path.
    
    Args:
        obj: Nested structure to traverse
        path: Either dot-separated string ("a.0.b") or tuple of keys
        default: Value to return if path doesn't exist
            
    Returns:
        Value at path or default if provided
            
    Raises:
        TypeError: If obj is not a container
        KeyError: If path doesn't exist and no default provided
        
    Examples:
        >>> data = {"a": {"b": [1, 2, {"c": 3}]}}
        >>> get_nested(data, "a.b.2.c")
        3
        >>> get_nested(data, ("a", "b", 2, "c"))
        3
        >>> get_nested(data, "x.y.z", default=None)
        None
    """
    if not is_container(obj):
        raise TypeError(f"Expected a Mapping or Sequence container, got {type(obj)}")
    
    if isinstance(path,str):
        keys = split_path(path)
    else:
        keys = path

    value=obj
    for key in keys:
        if is_container(value) and has_key(value,key):
            value = value[key]
        else:
            if default is not MISSING:
                return default
            else:
                raise KeyError(f"Path {path!r} not found in container")
    return value

def set_nested(obj:Container, path: Path, value):
    """Set a nested value, creating intermediate containers as needed.
    
    Creates missing containers (dict for string keys, list for integer keys)
    along the path if they don't exist.
    
    Args:
        obj: Container to modify 
        path: Path to set value at
        value: Value to set
        
    Raises:
        TypeError: If obj is not a container or if any container we attempt to write in is immutable
        
    Examples:
        >>> data = {}
        >>> set_nested(data, "a.b.0.c", 42)
        >>> data
        {'a': {'b': [{'c': 42}]}}
    """
    if not is_container(obj):
        raise TypeError(f"Expected a Mapping or Sequence container, got {type(obj)}")
    
    if isinstance(path, str):
        path = split_path(path)
    current = obj
    for i,key in enumerate(path):
        if i==len(path)-1:
            #terminal key reached, we set the value and return
            set_key(current,key,value)
            return
        elif not has_key(current,key) or current[key] is MISSING:
            if isinstance(path[i+1],int):
                set_key(current,key,[])
            else:# str
                set_key(current,key,{})
            current = current[key]
        else:
            current = current[key]

def pop_nested(obj:Container, path:Path, default=MISSING):
    """deletes a nested key/index and returns the value (if found).
    If not found, returns default if provided, otherwise raises an error.
    If provided, default will be returned in ANY case of failure.
    This includes these cases:
        - the path doesn't exist or doesn't make sense in the structure
        - the path actually exists but ends in an immutable container in which we can't pop
    
    Args:
        obj: Container to modify
        path: Path to the value to delete
        
    Raises:
        TypeError: If obj is not a container, or we attempt to modify an immutable container
        KeyError: If path doesn't exist
    """
    if not is_container(obj):
        raise TypeError(f"Expected a Mapping or Sequence container, got {type(obj)}")

    if isinstance(path, str):
        path = split_path(path)

    current = obj
    try:
        for i, key in enumerate(path):
            if is_container(current) and has_key(current,key):
                if i == len(path) - 1:
                    if is_mutable_container(current):
                        value=current[key]
                        del current[key]
                        return value
                    else:
                        raise TypeError(f"Can't delete in an immutable container. Attempt to delete key={key!r} in {current} of immutable type {type(current)} caused this error.")
                current = current[key]
            else:
                raise KeyError(f"Path {path!r} not found in container")
            
    except (KeyError,TypeError):
        if default is not MISSING:
            return default
        else:
            raise

def del_nested(obj:Container, path:Path):
    """deletes a nested key/index (if found).
    
    Args:
        obj: Container to modify
        path: Path to the value to delete
        
    Raises:
        TypeError: If obj is not a container, or we attempt to modify an immutable container
        KeyError: If path doesn't exist
    
    
    """
    # delegate the logic to pop_nested, we just don't return the output
    pop_nested(obj,path)

def has_nested(obj:Container, path: Path):
    """Check if a nested path exists.
    
    Args:
        obj: Container to check
        path: Path to check for existence
        
    Returns:
        True if path exists, False otherwise
    """
    if not is_container(obj):
        raise TypeError(f"Expected a Mapping or Sequence container, got {type(obj)}")
    try:
        get_nested(obj,path)
        return True
    except KeyError:
        return False


def extract(obj:C, *extracted_keys: Key) -> C:
    """
    Extract specified keys from a container.
    
    Args:
        obj (Mapping or Sequence): The source container.
        keys (str): Keys to extract.
    Returns:
        (Mapping or Sequence): A container of same type containing only the specified keys.
    """
    if not is_container(obj):
        raise TypeError(f"Expected a Mapping or Sequence container, got {type(obj)}")
    return ((key, obj[key]) for key in keys(obj) if key in extracted_keys)

def exclude(obj:C, *excluded_keys: Key) -> C:
    """
    Exclude specified keys from a container.
    
    Args:
        obj (Mapping or Sequence): The source container.
        keys (str): Keys to exclude.
    Returns:
        Mapping or Sequence: A container of same type without the specified keys.
    """
    if not is_container(obj):
        raise TypeError(f"Expected a Mapping or Sequence container, got {type(obj)}")
    return ((key, obj[key]) for key in keys(obj) if key not in excluded_keys)

def walk(
    obj: Container,
    callback: Optional[CallbackFn] = None,
    filter: Optional[FilterFn] = None,
    excluded: Optional[Tuple[Type, ...]] = None
) -> Iterator[Tuple[str, Any]]:
    """Walk through a nested container yielding (path, value) pairs.
    
    Recursively traverses the container, yielding paths and values for leaf nodes.
    Leaves can be transformed by callback and filtered by the filter predicate.
    
    Args:
        obj: Container to traverse
        callback: Optional function to transform leaf values
        filter: Optional predicate to filter paths/values (receives path and value)
        excluded: Container types to treat as leaves (default: str, bytes, bytearray)
        
    Yields:
        Tuples of (path_string, value) for each leaf node
        If callback provided, value is transformed by callback
        If filter provided, only yields pairs that pass filter(path, value)
        
    Examples:
        >>> data = {"a": [1, {"b": 2}], "c": 3}
        >>> list(walk(data))
        [('a.0', 1), ('a.1.b', 2), ('c', 3)]
        >>> list(walk(data, callback=str))
        [('a.0', '1'), ('a.1.b', '2'), ('c', '3')]
    """

    def _walk(obj: Any, path: Tuple[Key, ...]) -> Iterator[Tuple[str, Any]]:
        if is_container(obj,excluded=excluded):
            for k, v in unroll(obj):
                yield from _walk(v, path + (k,))
        else:
            joined_path=join_path(path)
            if filter is None or filter(joined_path,obj):
                yield joined_path, callback(obj) if callback is not None else obj
        
    yield from _walk(obj, ())
    
def walked(
    obj: Container,
    callback: Optional[CallbackFn] = None,
    filter: Optional[FilterFn] = None,
    excluded: Optional[Tuple[Type, ...]] = None
) -> Dict[str, Any]:
    """Return a flattened dictionary of path:value pairs from a nested container.
    
    Similar to walk(), but returns a dictionary instead of an iterator.
    
    Args:
        obj: Container to traverse
        callback: Optional function to transform leaf values
        filter: Optional predicate to filter paths/values
        excluded: Container types to treat as leaves
        
    Returns:
        Dictionary mapping path strings to leaf values
        
    Examples:
        >>> data = {"a": [1, {"b": 2}], "c": 3}
        >>> walked(data)
        {'a.0': 1, 'a.1.b': 2, 'c': 3}
    """
    return dict(walk(obj,callback=callback,filter=filter,excluded=excluded))
 

def first_keys(walked:Dict[str,Any])->Set[Key]:
    """
    Return all the first keys encountered in walked paths
    """
    return set(split_path(p)[0] for p in walked)

def is_seq_based(walked:Dict[str,Any])->bool:
    """
    Determines if the walked structure was initially a Sequence
    """
    fk=first_keys(walked)
    return fk==set(range(len(fk)))

def unwalk(walked:Dict[str,Any])->MutableContainer:
    """
    Recontructs a nested structure from a flattened dict.
    Args:
        walked: (Dict[str,Any]) a path:value flattened dictionary
    Returns:
        (MutableContainer) : Reconstructed Nested list / dict structure 
    """
    if is_seq_based(walked):
        base=[]
    else:
        base={}

    for path,value in walked.items():
        set_nested(base,path,value)
    
    return base

def deep_equals(obj1:Container,obj2:Container,excluded:Optional[Tuple[Type,...]]=None)->bool:
    """
    Compares two nested structures deeply by comparing their walked dicts
    """
    return walked(obj1,excluded=excluded)==walked(obj2,excluded=excluded)

def diff_nested(
    obj1: Container,
    obj2: Container,
    path: Tuple[Key, ...] = ()
) -> Dict[str, Tuple[Any, Any]]:
    """Compare two nested structures and return their differences.
    
    Recursively compares two containers and returns a dictionary of differences.
    Keys are paths where values differ, values are tuples of (obj1_value, obj2_value).
    
    Args:
        obj1: First container to compare
        obj2: Second container to compare
        path: Current path in recursion (used internally)
        
    Returns:
        Dictionary mapping paths to value pairs that differ
        MISSING is used when a key exists in one container but not the other
        
    Examples:
        >>> a = {"x": 1, "y": {"z": 2}}
        >>> b = {"x": 1, "y": {"z": 3}, "w": 4}
        >>> diff_nested(a, b)
        {'y.z': (2, 3), 'w': (MISSING, 4)}
    """
    diffs: Dict[str, Tuple[Any, Any]] = {}

    if is_container(obj1) and is_container(obj2):
        keys1 = set(keys(obj1))
        keys2 = set(keys(obj2))
        all_keys = keys1.union(keys2)
        for key in all_keys:
            new_path = path + (key,)
            in_obj1 = has_key(obj1, key)
            in_obj2 = has_key(obj2, key)
            if in_obj1 and in_obj2:
                val1, val2 = obj1[key], obj2[key]
                if is_container(val1) and is_container(val2):
                    diffs.update(diff_nested(val1, val2, new_path))
                else:
                    if val1 != val2:
                        diffs[join_path(new_path)] = (val1, val2)
            elif in_obj1:
                diffs[join_path(new_path)] = (obj1[key], MISSING)
            elif in_obj2:
                diffs[join_path(new_path)] = (MISSING, obj2[key])
    else:
        if obj1 != obj2:
            diffs[join_path(path)] = (obj1, obj2)

    return diffs

def deep_merge(
    target: MutableContainer,
    src: Container,
    conflict_resolver: Optional[Callable[[Any, Any], Any]] = None
) -> None:
    """Deeply merge source container into target, modifying target in-place.
    
    For mappings:
    - If a key exists in both and both values are containers, merge recursively
    - Otherwise, src value overwrites target value (or uses conflict_resolver)
    
    For sequences:
    - Elements are merged by index
    - If src has more elements, they are appended to target
    
    Args:
        target: Mutable container to merge into
        src: Container to merge from
        conflict_resolver: Optional function to resolve value conflicts
            Takes (target_value, src_value), returns resolved value
        
    Raises:
        TypeError: If target and src are incompatible container types
        
    Examples:
        >>> target = {"a": 1, "b": {"x": 1}}
        >>> src = {"b": {"y": 2}, "c": 3}
        >>> deep_merge(target, src)
        >>> target
        {'a': 1, 'b': {'x': 1, 'y': 2}, 'c': 3}
    """
    if isinstance(target, MutableMapping) and isinstance(src, Mapping):
        for key, src_value in src.items():
            if has_key(target, key):
                target_value = target[key]
                if is_container(target_value) and is_container(src_value):
                    deep_merge(target_value, src_value, conflict_resolver)
                else:
                    target[key] = conflict_resolver(target_value, src_value) if conflict_resolver else src_value
            else:
                target[key] = src_value

    elif isinstance(target, MutableSequence) and isinstance(src, Sequence):
        for idx, src_value in enumerate(src):
            if idx < len(target):
                target_value = target[idx]
                if is_container(target_value) and is_container(src_value):
                    deep_merge(target_value, src_value, conflict_resolver)
                else:
                    target[idx] = conflict_resolver(target_value, src_value) if conflict_resolver else src_value
            else:
                target.append(src_value)
    else:
        raise TypeError("Types of 'target' and 'src' aren't compatibles for deep merging.")
