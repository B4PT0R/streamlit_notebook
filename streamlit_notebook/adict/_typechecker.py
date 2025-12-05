"""
TypeChecker - A comprehensive runtime type checking library
"""
import inspect
import types
import typing
from typing import Any, Dict, List, Set, Tuple, Union, Optional, Callable, TypeVar, get_origin, get_args
import collections
import collections.abc
import sys
import functools

#region: Errors

class TypeCheckException(Exception):
    pass

class TypeCheckError(TypeCheckException):
    """Exception raised for common type check errors"""
    pass

class TypeMismatchError(TypeCheckException):
    """Exception raised when a value doesn't match the type."""
    pass

class TypeCheckFailureError(TypeCheckException):
    """Exception raised for other uncaught or critical errors"""
    pass

class CoercionError(Exception):
    """Exception raised when coercion is not possible."""
    pass

#endregion

#region: TypeChecker Class
class TypeChecker:
    """
    A comprehensive runtime type checker that supports modern typing constructs.
    """
    
    def __init__(self):

        self.origin_to_type_map = {
            # Basic collections
            typing.List: list,
            typing.Tuple: tuple,
            typing.Dict: dict,
            typing.Set: set,
            typing.FrozenSet: frozenset,
            
            # Sequence abstractions
            typing.Sequence: collections.abc.Sequence,
            typing.MutableSequence: collections.abc.MutableSequence,
            
            # Mapping abstractions
            typing.Mapping: collections.abc.Mapping,
            typing.MutableMapping: collections.abc.MutableMapping,
            
            # Set abstractions
            typing.AbstractSet: collections.abc.Set,
            typing.MutableSet: collections.abc.MutableSet,
            
            # Collection abstractions
            typing.Collection: collections.abc.Collection,
            typing.Container: collections.abc.Container,
            typing.Sized: collections.abc.Sized,
            
            # Iterator types
            typing.Iterable: collections.abc.Iterable,
            typing.Iterator: collections.abc.Iterator,
            typing.Generator: collections.abc.Generator,
            typing.Reversible: collections.abc.Reversible,
            
            # Callable types
            typing.Callable: collections.abc.Callable,
            
            # Bytes-like types
            typing.ByteString: collections.abc.ByteString,
            
            # Additional sequence types
            typing.Deque: collections.deque,
            
            # Additional mapping types
            typing.DefaultDict: collections.defaultdict,
            typing.OrderedDict: collections.OrderedDict,
            typing.ChainMap: collections.ChainMap,
            typing.Counter: collections.Counter,
            
            # Additional set types
            # (None needed, Set and FrozenSet cover the built-ins)
            
            # View types
            typing.KeysView: collections.abc.KeysView,
            typing.ItemsView: collections.abc.ItemsView,
            typing.ValuesView: collections.abc.ValuesView,
            
            # Async types (if we want to support them)
            typing.AsyncIterator: collections.abc.AsyncIterator,
            typing.AsyncIterable: collections.abc.AsyncIterable,
            typing.AsyncGenerator: collections.abc.AsyncGenerator,
            typing.Coroutine: collections.abc.Coroutine,
            typing.Awaitable: collections.abc.Awaitable,
            
            # Additional ABCs from collections.abc
            typing.Hashable: collections.abc.Hashable,
        }
        
        self.type_checkers = {
            # Basic collections
            (typing.List, list): self._check_sequence_like,
            (typing.Tuple, tuple): self._check_tuple_like,
            (typing.Dict, dict): self._check_mapping_like,
            (typing.Set, set): self._check_set_like,
            (typing.FrozenSet, frozenset): self._check_set_like,
            
            # Sequence abstractions
            (typing.Sequence, collections.abc.Sequence): self._check_sequence_like,
            (typing.MutableSequence, collections.abc.MutableSequence): self._check_sequence_like,
            
            # Mapping abstractions
            (typing.Mapping, collections.abc.Mapping): self._check_mapping_like,
            (typing.MutableMapping, collections.abc.MutableMapping): self._check_mapping_like,
            
            # Set abstractions
            (typing.AbstractSet, collections.abc.Set): self._check_set_like,
            (typing.MutableSet, collections.abc.MutableSet): self._check_set_like,
            
            # Collection abstractions
            (typing.Collection, collections.abc.Collection): self._check_collection_like,
            (typing.Container, collections.abc.Container): self._check_container_like,
            (typing.Sized, collections.abc.Sized): lambda h, v: isinstance(v, collections.abc.Sized),
            
            # Iterator types
            (typing.Iterable, collections.abc.Iterable): self._check_iterable_like,
            (typing.Iterator, collections.abc.Iterator): self._check_iterator_like,
            (typing.Generator, collections.abc.Generator): self._check_iterator_like,
            (typing.Reversible, collections.abc.Reversible): lambda h, v: isinstance(v, collections.abc.Reversible),
            
            # Callable types
            (typing.Callable, collections.abc.Callable): self._check_callable,
            
            # View types
            (typing.KeysView, collections.abc.KeysView): self._check_mapping_view,
            (typing.ItemsView, collections.abc.ItemsView): self._check_mapping_view,
            (typing.ValuesView, collections.abc.ValuesView): self._check_mapping_view,
            
            # ByteString types
            (typing.ByteString, collections.abc.ByteString): lambda h, v: isinstance(v, collections.abc.ByteString),
            
            # Additional collection types with concrete implementations
            (typing.Deque, collections.deque): self._check_sequence_like,
            (typing.OrderedDict, collections.OrderedDict): self._check_mapping_like,
            (typing.DefaultDict, collections.defaultdict): self._check_mapping_like,
            (typing.ChainMap, collections.ChainMap): self._check_mapping_like,
            (typing.Counter, collections.Counter): self._check_mapping_like,
        }

    #region: entry point
    def check_type(self, hint: Any, value: Any) -> bool:
        """
        Check if a value matches the given type hint.
        Main entry point of the TypeChecker class
        
        Args:
            hint: A type annotation or typing construct
            value: The value to check against the type hint
            
        Returns:
            bool: True if the value matches the type hint
            
        Raises:
            TypeMismatchError: When the value doesn't match the type hint
            TypeCheckError: When some minor error made the type check impossible
            TypeCheckFailureError: When any other uncaught exception occurs
        """
        try:
            result = self._check_type_internal(hint, value)
            if not isinstance(result, bool):
                raise TypeCheckFailureError(
                    f"_check_type_internal returned non-boolean value: {result}"
                )
            if not result:
                raise TypeMismatchError()
            return result
        except TypeMismatchError:
            raise
        except TypeCheckError:
            raise
        except Exception as e:
            raise TypeCheckFailureError(f"Error during type checking: {str(e)}")
    #endregion

    #region: hint parsing

    def _origin_to_type(self,origin):
        return self.origin_to_type_map.get(origin,origin)

    def _is_generic_class(self, hint):
        """Check if a hint is a generic class that can be parameterized."""
        # Check if it's a type with __parameters__
        is_parameterized = isinstance(hint, type) and hasattr(hint, '__parameters__')
        
        # Also check for typing.Generic in bases
        if isinstance(hint, type):
            bases = getattr(hint, '__mro__', ())
            has_generic_base = typing.Generic in bases
            return is_parameterized or has_generic_base
        
        return is_parameterized
            
    def _is_protocol(self, hint):
        """
        Comprehensive protocol detection that handles both special form Protocol 
        and concrete protocol classes without relying on _is_special_form.
        """
        # Check for the protocol marker attribute on the hint itself
        is_protocol_class = isinstance(hint, type) and getattr(hint, '_is_protocol', False)
        
        # Check for Protocol special form directly
        name = getattr(hint, '_name', None)
        is_protocol_special_form = name == 'Protocol'
        
        # Check origin for parameterized protocols
        origin = get_origin(hint)
        if origin is not None:
            origin_name = getattr(origin, '_name', None)
            origin_is_protocol = origin_name == 'Protocol' or getattr(origin, '_is_protocol', False)
        else:
            origin_is_protocol = False
        
        return is_protocol_class or is_protocol_special_form or origin_is_protocol
    
    def _is_newtype(self,hint):
        return hasattr(hint, '__supertype__')
    
    def _is_basic_type(self,hint):
        return isinstance(hint,type) and not self._is_protocol(hint) and not self._is_generic_class(hint) and not self._is_newtype(hint)

    def _is_generic_alias(self, hint):
        """
        Check if a hint is a generic alias like List[int], Dict[str, int], etc.
        Handles different implementations across Python versions.
        
        Args:
            hint: The type hint to check
            
        Returns:
            bool: True if the hint is a generic alias
        """
        # First check if it's a special form - if so, it's not considered a generic alias
        if self._is_special_form(hint):
            return False
            
        # Now check generic alias indicators
        return (hasattr(typing, '_GenericAlias') and isinstance(hint, typing._GenericAlias) or
                hasattr(typing, 'GenericAlias') and isinstance(hint, typing.GenericAlias) or
                hasattr(typing, '_SpecialGenericAlias') and isinstance(hint, typing._SpecialGenericAlias) or
                hasattr(types, 'GenericAlias') and isinstance(hint, types.GenericAlias) or
                getattr(hint, '__origin__', None) is not None)

    def _is_typeddict(self, hint):
        """Check if a hint is a TypedDict."""
        return hasattr(hint, "__annotations__") and hasattr(hint, "__total__")

    def _is_special_form(self, hint):
        """
        Check if a hint is a special form (Union, Optional, ClassVar, etc.).
        Uses a consistent approach that works across Python versions.
        
        Args:
            hint: The type hint to check
            
        Returns:
            bool: True if the hint is a special form
        """

        # Handle PEP 604 union types (Python 3.10+)
        if hasattr(types, "UnionType") and isinstance(hint, types.UnionType):
            return True

        # Known special form names for validation (Protocols are handled separately)
        special_form_names = {
            'Union', 'Optional', 'ClassVar', 'Final', 'Literal',
            'TypeGuard', 'ParamSpec', 'Concatenate', 'Annotated'
        }
        
        # The most reliable approach: check the name attribute
        name = None
        
        # For parameterized special forms, get name from origin
        origin = get_origin(hint)
        if origin is not None:
            name = getattr(origin, '_name', None)
        
        # For direct special forms, get name directly
        if name is None:
            name = getattr(hint, '_name', None)
        
        # Return True if we found a matching name
        return name in special_form_names

    def _get_special_form_name(self, hint):
        """
        Get the name of a special form type hint.
        Works with both direct special forms and parameterized ones.
        
        Args:
            hint: A special form type hint (e.g., Union, Optional)
            
        Returns:
            str or None: The name of the special form, or None if not found
        """
        # For parameterized special forms, get the name from the origin
        origin = get_origin(hint)
        if origin is not None:
            name = getattr(origin, '_name', None)
            if name:
                return name
                    
        # For direct special forms, get the name directly
        return getattr(hint, '_name', None)
    
    def _is_box_like_generic(self, origin, args, value):
        """
        Check if this is a Box-like generic class with a 'value' attribute.
        Used for handling simple generic wrapper classes.
        
        Args:
            origin: The origin type
            args: The type arguments
            value: The value to check
            
        Returns:
            bool: True if this is a Box-like generic with a 'value' attribute
        """
        return (origin is not None and 
                hasattr(value, '__class__') and
                args and 
                len(args) == 1 and 
                hasattr(value, 'value'))

    def _is_parameterized_generic(self, origin, hint):
        """
        Check if this is a generic class with type parameters.
        
        Args:
            origin: The origin type
            hint: The type hint
            
        Returns:
            bool: True if this is a parameterized generic class
        """
        return ((origin is not None and hasattr(origin, '__parameters__')) or 
                (origin is None and hasattr(hint, '__parameters__')))

    def _is_special_origin(self, origin):
        """
        Check if an origin type is a special form.
        
        Args:
            origin: The origin type to check
            
        Returns:
            bool: True if the origin is a special form
        """
        return getattr(origin, '_special', False)

    #endregion

    #region: core logic

    def _check_basic_type(self,hint,value):
        """
        Similar to isinstance check but doesn't accept booleans as int
        """
        if hint is int:
            return isinstance(value, int) and not isinstance(value,bool)
        return isinstance(value,hint)

    def _check_type_internal(self, hint: Any, value: Any) -> bool:
        """
        Internal method to check if a value matches the given type hint.
        This is the core recursive method that handles all type hint varieties.
        
        Args:
            hint: A type annotation or typing construct
            value: The value to check against the type hint
            
        Returns:
            bool: True if the value matches the type hint, False otherwise
            
        Raises:
            TypeCheckError: When some error made the type check impossible
        """
        # Handle None/NoneType special case
        if hint in (None, type(None)):
            return value is None
        
        # Special case for Any and object
        if hint in (Any, object):
            return True
        
        # Case 9: TypedDict
        if self._is_typeddict(hint):
            return self._check_typeddict(hint, value)

        # Handle Self type (PEP 673)
        if hasattr(typing, "Self") and hint is typing.Self:
            # For Self, check if value is an instance of the class that contains the annotation
            # This is a simplified approach - we can't truly know the containing class
            # but we can check against the value's own class
            return isinstance(value, value.__class__)
        
        # Case 1: Protocol check
        if self._is_protocol(hint):
            return self._check_protocol(hint, value)
        
        # Case 2: Special form (Union, Optional, etc.)
        if self._is_special_form(hint):
            return self._check_special_form(hint,value)
                
        # Case 3: Generic alias (List[int], Dict[str, int], Callable[[int,str],int], etc.)
        if self._is_generic_alias(hint):
            return self._check_generic_alias(hint, value)
        
        # Case 4: Generic Classes
        if self._is_generic_class(hint):
            return self._check_generic_typevar(hint, value)

        # Case 5: Basic type check (int, str, etc.)
        if self._is_basic_type(hint):
            return self._check_basic_type(hint, value)
        
        # Case 6: TypeVar
        if isinstance(hint, TypeVar):
            return self._check_typevar(hint, value)
                    
        # Case 7: Forward references (strings)
        if isinstance(hint, str):
            return self._check_forward_ref(hint, value)
            
        # Case 8: NewType
        if self._is_newtype(hint):
            return self._check_type_internal(hint.__supertype__, value)
            
        # Unknown type hint
        raise TypeCheckError(f"Unsupported type hint: {hint}")

    def _check_special_form(self, hint, value):
        """
        Handle type checking for all special forms.
        
        Args:
            hint: A special form type hint (e.g., Union[int, str], Optional[int])
            value: The value to check
            
        Returns:
            bool: True if the value matches the special form
            
        Raises:
            TypeCheckError: For unsupported or invalid special forms
        """

        # Handle PEP 604 union types (Python 3.10+)
        if hasattr(types, "UnionType") and isinstance(hint, types.UnionType):
            # Delegate to _check_union for PEP 604 unions (int | str)
            return self._check_union(hint, value)
        
        origin = get_origin(hint)
        form_name = self._get_special_form_name(hint)
        
        # Union and Optional handling
        if form_name == 'Union' or (origin in (typing.Union, Union)):
            return self._check_union(hint, value)
        
        # Optional is a special case of Union[T, None]
        if form_name == 'Optional':
            return self._check_optional(hint,value)
        
        # ClassVar handling
        if form_name == 'ClassVar':
            return self._check_classvar(hint,value)
        
        # Final handling
        if form_name == 'Final':
            return self._check_final(hint,value)
        
        # Literal handling
        if form_name == 'Literal':
            return self._check_literal(hint,value)
        
        # TypeGuard handling (Python 3.10+)
        if form_name == 'TypeGuard':
            return True  # TypeGuard is a runtime no-op
        
        # ParamSpec handling (Python 3.10+)
        if form_name == 'ParamSpec':
            return True  # ParamSpec is a runtime no-op
        
        # Concatenate handling (Python 3.10+)
        if form_name == 'Concatenate':
            return True  # Concatenate is a runtime no-op
        
        # Annotated handling (Python 3.9+)
        if form_name == 'Annotated':
            self._check_annotated(hint,value)
        
        # Unknown special form
        raise TypeCheckError(f"Unsupported special form: {form_name}")

    def _check_generic_alias(self,hint,value):
        origin = get_origin(hint)
        args = get_args(hint)
            
        # Case 2: Generic classes with type parameters
        if self._is_parameterized_generic(origin, hint):
            return self._check_generic_typevar(hint, value)
        
        # Case 3: Standard origins
        if (checker:=self._get_checker(origin)) is not None:
            return checker(hint,value)
        
        # Case 4: Generic typevar
        if isinstance(origin,typing.Generic):
            return self._check_generic_typevar(hint,value)
        
        # Case 5: Fall back to origin type check
        if origin is not None:
            if self._is_special_origin(origin):
                return self._check_special_form(hint, value)
            return self._check_basic_type(origin, value)
        
        # Case 6: Custom generic classes where origin is None
        if hasattr(hint, '__origin__'):
            if self._is_special_origin(hint.__origin__):
                return self._check_special_form(hint, value)
            return self._check_basic_type(hint.__origin__, value)
        
        # Unknown generic alias
        raise TypeCheckError(f"Unsupported generic alias: {hint}")

    def _get_checker(self, origin):
        """
        Get the appropriate checker method for a type registered in self.type_checkers.
        Handles both standard typing types and their corresponding collections.abc's.
        
        Args:
            origin: The origin type to find a checker for
            
        Returns:
            function or None: The checker method for the origin, or None if not found
        """

        for type_key, checker_method in self.type_checkers.items():
            if origin in type_key:
                return checker_method        
        return None

    #endregion

    #region: Generic type checkers

    def _check_typeddict(self, hint, value):
        """
        Check if a value matches a TypedDict type hint.
        
        Args:
            hint: A TypedDict type hint
            value: The value to check
            
        Returns:
            bool: True if the value is a dict with the expected keys and value types
        """
        if not isinstance(value, dict):
            return False
        
        annotations = getattr(hint, "__annotations__", {})
        is_total = getattr(hint, "__total__", True)
        
        # Check if all required keys are present
        if is_total:
            for key in annotations:
                if key not in value:
                    return False
        
        # Check that all values match their expected types
        for key, val in value.items():
            if key in annotations:
                expected_type = annotations[key]
                
                # Check if the value matches the expected type
                if not self._check_type_internal(expected_type, val):
                    return False
        
        return True

    def _check_collection_like(self, hint, value):
        """
        Check if a value matches the Collection protocol.
        Collection = Sized + Iterable + Container.
        
        Args:
            hint: The Collection type hint
            value: The value to check
            
        Returns:
            bool: True if value matches Collection protocol and its elements
        """
        origin=get_origin(hint) or hint
        args = get_args(hint)

        if not isinstance(value, self._origin_to_type(origin)):
            return False
            
        if len(args) != 1:
            raise TypeCheckError("Collection requires exactly 1 type argument")
            
        elem_type = args[0]
        
        # If it's an iterator, we can't safely check elements
        if isinstance(value, collections.abc.Iterator):
            return True
            
        # Check each element
        return all(self._check_type_internal(elem_type, item) for item in value)

    def _check_container_like(self, hint, value):
        """
        Check if a value matches the Container protocol.
        Container just requires __contains__.
        
        Args:
            hint: The Container type hint
            value: The value to check
            
        Returns:
            bool: True if value is a container
        """
        origin=get_origin(hint) or hint
        args = get_args(hint)

        if not isinstance(value, self._origin_to_type(origin)):
            return False
            
        args = get_args(hint)
        if len(args) != 1:
            raise TypeCheckError("Container requires exactly 1 type argument")
        
        # We can't reliably check what the container can contain
        # without trying every possible value, so we just check it's a container
        return True

    def _check_mapping_view(self, hint, value):
        """
        Check if a value matches a mapping view type (KeysView, ItemsView, or ValuesView).
        
        Args:
            hint: The mapping view type hint
            value: The value to check
            
        Returns:
            bool: True if value matches the view type and its elements
        """
        
        origin=get_origin(hint) or hint
        args = get_args(hint)

        if not isinstance(value, self._origin_to_type(origin)):
            return False
            
        args = get_args(hint)
        
        # KeysView and ValuesView take one type argument
        if origin in (typing.KeysView, typing.ValuesView):
            if len(args) != 1:
                raise TypeCheckError(f"{origin._name} requires exactly 1 type argument")
                
            # We can't reliably check the elements without consuming the view
            # or accessing the underlying mapping
            return True
            
        # ItemsView takes two type arguments (key type and value type)
        if origin == typing.ItemsView:
            if len(args) != 2:
                raise TypeCheckError("ItemsView requires exactly 2 type arguments")
                
            # Similarly, we can't reliably check the elements
            return True
            
        return True

    def _check_tuple_like(self, hint, value):
        """
        Check if a value matches a generic tuple-like type.
        Tuples are special as they can be either homogeneous (Tuple[int, ...]) 
        or heterogeneous (Tuple[int, str, bool]).
        
        Args:
            hint: A generic tuple-like type
            value: The value to check
            
        Returns:
            bool: True if value matches the tuple type specification
        """

        origin=get_origin(hint) or hint
        args = get_args(hint)

        if not isinstance(value, self._origin_to_type(origin)):
            return False
        
        # Empty tuple - Tuple[()]
        if len(args) == 1 and args[0] == ():
            return len(value) == 0
                
        # Variable length tuple - Tuple[int, ...]
        if len(args) == 2 and args[1] is ...:
            elem_type = args[0]
            return all(self._check_type_internal(elem_type, item) for item in value)
                
        # Fixed length tuple - Tuple[int, str, bool]
        if len(value) != len(args):
            return False
                
        return all(self._check_type_internal(args[i], value[i]) 
                for i in range(len(value)))
    
    def _check_sequence_like(self, hint, value):
        """
        Base method for checking homogeneous sequence-like collections.
        Used for List, Sequence, MutableSequence, etc.
        
        Args:
            hint: The sequence type hint
            value: The value to check
        """
        origin=get_origin(hint) or hint
        args = get_args(hint)

        if not isinstance(value, self._origin_to_type(origin)):
            return False
        
        if len(args) != 1:
            raise TypeCheckError(f"Sequence type requires exactly 1 type argument")
            
        elem_type = args[0]
        
        # Handle iterators specially - don't consume them
        if isinstance(value, collections.abc.Iterator):
            return True
            
        return all(self._check_type_internal(elem_type, item) for item in value)

    def _check_set_like(self, hint, value):
        """
        Base method for checking set-like collections (unordered, unique elements).
        Used for Set, MutableSet, FrozenSet, etc.
        
        Args:
            hint: The set type hint
            value: The value to check
        """
        origin=get_origin(hint) or hint
        args = get_args(hint)

        if not isinstance(value, self._origin_to_type(origin)):
            return False
        
        if len(args) != 1:
            raise TypeCheckError(f"Set type requires exactly 1 type argument")
            
        elem_type = args[0]
        
        # Empty set is valid
        if not value:
            return True
            
        return all(self._check_type_internal(elem_type, item) for item in value)
    
    def _check_mapping_like(self, hint, value):
        """
        Base method for checking mapping-like collections (key-value pairs).
        Used for Dict, Mapping, MutableMapping, etc.
        
        Args:
            hint: The mapping type hint
            value: The value to check
            expected_type: The expected container type
        """
        origin=get_origin(hint) or hint
        args = get_args(hint)

        if not isinstance(value, self._origin_to_type(origin)):
            return False
        
        if len(args) != 2:
            raise TypeCheckError(f"Mapping type requires exactly 2 type arguments")
            
        key_type, value_type = args
        
        # Empty mapping is valid
        if not value:
            return True
            
        return all(
            self._check_type_internal(key_type, k) and 
            self._check_type_internal(value_type, v) 
            for k, v in value.items()
        )

    def _check_iterable_like(self, hint, value):
        """
        Check if a value matches a generic iterable type.
        For non-iterator iterables (like lists, sets), validates all elements.
        For iterators, only checks the type without validating elements.
        
        Args:
            hint: A generic iterable type (e.g., Iterable[int])
            value: The value to check
            
        Returns:
            bool: True if the value is an iterable with elements matching the element type
                For iterators, only checks that it's an iterator without validating elements
        """
        origin=get_origin(hint) or hint
        args = get_args(hint)

        if not isinstance(value, self._origin_to_type(origin)):
            return False
                
        if len(args) != 1:
            raise TypeCheckError(f"Iterable requires exactly 1 type argument, got {len(args)}")
                
        elem_type = args[0]
        
        # If it's an iterator, we can't safely check elements without consuming it
        if isinstance(value, collections.abc.Iterator):
            return True  # Only check that it's an iterator, not what it yields
        
        # For non-iterator iterables (lists, sets, etc.), check all elements
        try:
            for item in value:
                if not self._check_type_internal(elem_type, item):
                    return False
            return True
        except TypeError:
            # Fall back to just validating it's an iterable
            return True

    def _check_iterator_like(self, hint, value):
        """
        Check if a value matches a generic iterator type.
        Only validates that the object is an iterator, not what it yields.
        
        Args:
            hint: A generic iterator type (e.g., Iterator[int])
            value: The value to check
            
        Returns:
            bool: True if the value is an iterator (element types are not validated)
        """
        origin=get_origin(hint) or hint
        args = get_args(hint)

        if not isinstance(value, self._origin_to_type(origin)):
            return False
                
        if len(args) != 1:
            raise TypeCheckError(f"Iterator requires exactly 1 type argument, got {len(args)}")
        
        # We intentionally don't validate iterator elements to avoid consuming the iterator
        return True

    #endregion

    #region: Special form checkers

    def _check_union(self, hint, value):
        """
        Check if a value matches any type in a Union.
        
        Args:
            hint: A Union type hint (e.g., Union[int, str])
            value: The value to check
            
        Returns:
            bool: True if the value matches any type in the Union
            
        Raises:
            TypeCheckError: If the Union has no type arguments
        """
        args = get_args(hint)
        if not args:
            raise TypeCheckError("Union requires at least one type argument")
        for arg in args:
            if self._check_type_internal(arg, value):
                return True
        return False

    def _check_optional(self, hint, value):
        """
        Check if a value matches an Optional type hint.
        Optional[X] is equivalent to Union[X, None].
        
        Args:
            hint: An Optional type hint
            value: The value to check
            
        Returns:
            bool: True if the value is None or matches the type argument
            
        Raises:
            TypeCheckError: If the Optional has invalid arguments
        """
        args = get_args(hint)
        if len(args) != 1:
            raise TypeCheckError(f"Optional requires exactly 1 type argument, got {len(args)}")
        
        if value is None:
            return True
            
        return self._check_type_internal(args[0], value)

    def _check_classvar(self, hint, value):
        """
        Check if a value matches a ClassVar type hint.
        ClassVar[X] checks against the underlying type X.
        
        Args:
            hint: A ClassVar type hint
            value: The value to check
            
        Returns:
            bool: True if the value matches the type X in ClassVar[X]
            
        Raises:
            TypeCheckError: If the ClassVar has invalid arguments
        """
        args = get_args(hint)
        if len(args) != 1:
            raise TypeCheckError(f"ClassVar requires exactly 1 type argument, got {len(args)}")
        
        # Just check against the contained type - don't try to use isinstance with ClassVar
        return self._check_type_internal(args[0], value)

    def _check_final(self, hint, value):
        """
        Check if a value matches a Final type hint.
        Final without arguments accepts any value, Final[X] checks against type X.
        
        Args:
            hint: A Final type hint
            value: The value to check
            
        Returns:
            bool: True if the value matches the Final type
            
        Raises:
            TypeCheckError: If the Final has invalid arguments
        """
        args = get_args(hint)
        if not args:
            return True  # Final without args accepts any value
            
        if len(args) != 1:
            raise TypeCheckError(f"Final requires exactly 0 or 1 type arguments, got {len(args)}")
            
        return self._check_type_internal(args[0], value)

    def _check_literal(self, hint, value):
        """
        Check if a value matches a Literal type hint.
        Literal[x, y, z] accepts only the exact values x, y, or z.
        
        Args:
            hint: A Literal type hint
            value: The value to check
            
        Returns:
            bool: True if the value is one of the literal values
        """
        args = get_args(hint)
        return value in args
    
    def _check_forward_ref(self,hint,value):
        """
        Check if a value matches a forward reference type hint.
        Attempts to resolve the string-based type reference in appropriate scopes.
        
        Args:
            hint: A string representing a forward reference type
            value: The value to check
            
        Returns:
            bool: True if the value matches the resolved type
            
        Raises:
            TypeCheckError: If the forward reference cannot be resolved
        """
        frame = inspect.currentframe()
        try:
            resolved_type = self._resolve_forward_ref(hint, frame.f_back)
            return self._check_type_internal(resolved_type, value)
        finally:
            del frame  # Avoid reference cycles

    def _check_annotated(self,hint,value):
        """
        Check if a value matches an Annotated type hint.
        Only checks against the first type argument, ignoring metadata.
        
        Args:
            hint: An Annotated type hint
            value: The value to check
            
        Returns:
            bool: True if the value matches the base type
            
        Raises:
            TypeCheckError: If the Annotated has no type arguments
        """
        args = get_args(hint)
        if not args:
            raise TypeCheckError("Annotated requires at least one type argument")
        return self._check_type_internal(args[0], value)

    
    def _check_typevar(self,hint,value):
        """
        Check if a value matches a TypeVar.
        Handles TypeVars with constraints, bounds, or neither.
        
        Args:
            hint: A TypeVar
            value: The value to check
            
        Returns:
            bool: True if the value matches the TypeVar's constraints/bounds
        """
        # If TypeVar has constraints, check against those
        if hint.__constraints__:
            return any(self._check_type_internal(constraint, value) 
                    for constraint in hint.__constraints__)
        # If TypeVar has a bound, check against that
        if hint.__bound__:
            return self._check_type_internal(hint.__bound__, value)
        # Otherwise, accept any value (just like Any)
        return True


    def _get_abc_checker(self,origin):
        """
        Find the appropriate checker method for a type that might inherit from an ABC.
        Walks up the MRO chain to find any registered ABC base classes and returns 
        their corresponding checker method.
        
        Args:
            origin: The origin type to find a checker for
                Could be a custom collection type inheriting from ABC classes
                e.g., MySequence that inherits from collections.abc.Sequence
        
        Returns:
            function or None: The checker method for the ABC base class if found,
                None if no matching ABC base class is found
                
        Examples:
            For a custom sequence class:
            >>> class MySequence(collections.abc.Sequence, Generic[T]): ...
            The method would:
            1. Find Sequence in the MRO
            2. Map it to collections.abc.Sequence in origin_to_type_map
            3. Return the sequence checker method from type_checkers
        """
        checker=None
        if isinstance(origin, type):
            for base in origin.__mro__[1:]:  # Skip self
                # Look for the base in values of origin_to_type_map
                for typing_type, concrete_type in self.origin_to_type_map.items():
                    if issubclass(base, concrete_type):
                        # Find the corresponding checker for this type
                        checker=self._get_checker(concrete_type)
                        break
                if checker is not None:
                    break
        return checker

    def _substitute_typevars(self, hint, typevar_map):
        """
        Substitute TypeVars in a type hint with their concrete types.
        
        Args:
            hint: The type hint that may contain TypeVars
            typevar_map: A mapping from TypeVars to their concrete types
        
        Returns:
            A type hint with TypeVars replaced by their concrete types
        """
        # If hint is a TypeVar directly, substitute it
        if isinstance(hint, TypeVar) and hint in typevar_map:
            return typevar_map[hint]
        
        # If hint is not a generic, return it as is
        origin = get_origin(hint)
        if origin is None:
            return hint
        
        # Get the arguments of the generic
        args = get_args(hint)
        if not args:
            return hint
        
        # Substitute TypeVars in the arguments
        new_args = tuple(self._substitute_typevars(arg, typevar_map) for arg in args)
        
        # Reconstruct the generic with substituted arguments
        try:
            return origin[new_args]
        except (TypeError, IndexError):
            # If reconstruction fails, return the original hint
            return hint

    def _check_generic_class_attributes(self, origin, expected_args, value):
        """
        Check if a generic class instance's attributes match the expected types
        based on the class's type annotations, including inherited annotations.
        
        Args:
            origin: The origin type (the generic class itself)
            expected_args: The expected type arguments for the generic class
            value: The instance to check
        
        Returns:
            bool: True if all annotated attributes match their expected types
        """
        # Get the TypeVars from the class definition
        typevars = getattr(origin, "__parameters__", [])
        
        # If there are no TypeVars, there's nothing to check
        if not typevars:
            return True
        
        # Collect annotations from the class and its bases
        all_annotations = {}
        
        # Start with the class itself
        if hasattr(origin, "__annotations__"):
            all_annotations.update(origin.__annotations__)
        
        # Get annotations from base classes
        for base in getattr(origin, "__mro__", [])[1:]:  # Skip self
            if hasattr(base, "__annotations__"):
                # Only add annotations we don't already have
                for name, type_hint in base.__annotations__.items():
                    if name not in all_annotations:
                        all_annotations[name] = type_hint
        
        # Create a mapping of TypeVars to their concrete types
        typevar_map = {tv: expected_args[i] for i, tv in enumerate(typevars) if i < len(expected_args)}
        
        # For each annotation, check the attribute
        for attr_name, attr_type in all_annotations.items():
            # If the attribute exists, check its type
            if hasattr(value, attr_name):
                attr_value = getattr(value, attr_name)
                
                # Substitute TypeVars with their concrete types in the attribute's type
                concrete_type = self._substitute_typevars(attr_type, typevar_map)
                
                # Check if the attribute's value matches the concrete type
                if not self._check_type_internal(concrete_type, attr_value):
                    return False
        
        # Handle inherited generic classes
        # For example, if SubBox inherits from MultiBox[T, str, bool]
        # we need to map T -> the actual type from expected_args
        
        # Get the bases of the class with type arguments
        for base_with_args in getattr(origin, "__orig_bases__", []):
            base_origin = get_origin(base_with_args)
            if base_origin is None:
                continue
            
            # Get the base class's TypeVars
            base_typevars = getattr(base_origin, "__parameters__", [])
            if not base_typevars:
                continue
                
            # Get the type arguments of the base as used in the class definition
            base_args = get_args(base_with_args)
            if not base_args:
                continue
            
            # Create a mapping from base TypeVars to actual types
            typevar_map = {}
            
            for i, base_arg in enumerate(base_args):
                if isinstance(base_arg, TypeVar):
                    if base_arg in typevars:
                        # This is one of our class's TypeVars (e.g., T in SubBox(MultiBox[T, str, bool]))
                        typevar_index = typevars.index(base_arg)
                        if typevar_index < len(expected_args):
                            # Map this TypeVar to the actual type from expected_args
                            typevar_map[base_arg] = expected_args[typevar_index]
                else:
                    # This is a concrete type (e.g., str, bool)
                    if i < len(base_typevars):
                        # Map the base class's TypeVar to this concrete type
                        typevar_map[base_typevars[i]] = base_arg
            
            # Check base class attributes with the mapped types
            for attr_name, attr_type in getattr(base_origin, "__annotations__", {}).items():
                if isinstance(attr_type, TypeVar) and attr_type in typevar_map:
                    expected_type = typevar_map[attr_type]
                    
                    # Check if the attribute exists
                    if hasattr(value, attr_name):
                        attr_value = getattr(value, attr_name)
                        
                        # Check if the attribute's value matches the expected type
                        if not self._check_type_internal(expected_type, attr_value):
                            return False
        
        return True

    def _check_generic_typevar(self, hint, value):
        """
        Check if a value matches a Generic type with TypeVar parameters.
        Handles both custom collection types and simple generic classes.
        
        The method handles several cases:
        1. Custom collection types inheriting from ABCs (e.g., MySequence[int])
        - Uses ABC checkers to validate both the protocol and element types
        2. Simple generic classes with value attributes (e.g., Box[int])
        - Checks the .value attribute against the type parameter
        3. Generic classes with original type info (e.g., through __orig_class__)
        - Compares actual type args against expected ones
        
        Args:
            hint: A Generic type with optional type parameters
                Examples: Box[int], MySequence[str], Container[float]
            value: The value to check against the generic type
        
        Returns:
            bool: True if the value matches the generic type and its parameters
                For collection types: must match both the protocol and element types
                For simple generics: must match the class and type parameters
        
        Examples:
            >>> class MySequence(Sequence, Generic[T]): ...
            >>> seq = MySequence([1, 2, 3])
            >>> _check_generic_typevar(MySequence[int], seq)  # Uses sequence checker
            True
            
            >>> class Box(Generic[T]):
            ...     def __init__(self, value: T): self.value = value
            >>> box = Box(42)
            >>> _check_generic_typevar(Box[int], box)  # Checks value attribute
            True
        """
        # Get the origin type (e.g., Box from Box[int])
        origin = get_origin(hint)
        
        if origin is None:
            origin = hint
        
        # First, check if the value is an instance of the origin
        is_instance = self._check_basic_type(origin,value)
        
        if not is_instance:
            return False
        
        # Get the expected type arguments
        expected_args = get_args(hint)
        
        if not expected_args:
            return True  # No type arguments to check

        # Check if this is a custom collection type by looking for ABC bases
        if (checker:=self._get_abc_checker(origin)) is not None:
            return checker(hint,value)

        # Get the actual type arguments from the value's class or instance
        actual_args = []
        
        # Try multiple ways to get the type arguments
        if hasattr(value, "__orig_class__"):
            actual_args = get_args(value.__orig_class__)
        
        if not actual_args and hasattr(value.__class__, "__orig_class__"):
            actual_args = get_args(value.__class__.__orig_class__)

        # Get the actual type arguments from the value's class or instance
        actual_args = []
        
        # Check the attributes based on annotations
        if not self._check_generic_class_attributes(origin, expected_args, value):
            return False
        
        # If we have actual type arguments, compare them with expected
        if actual_args:
            if len(expected_args) != len(actual_args):
                return False
            
            for expected, actual in zip(expected_args, actual_args):
                if expected != actual:
                    # Allow subclass relationship
                    is_subclass = (isinstance(expected, type) and 
                                isinstance(actual, type) and 
                                issubclass(actual, expected))
                    
                    if not is_subclass:
                        return False
        
        # If we get here, either:
        # 1. We couldn't determine actual args but the value attribute passed
        # 2. We compared actual args and they matched
        return True

    def _check_callable(self,hint,value):
        """
        Check if a value matches a Callable type with specific argument and return types.
        
        Args:
            hint: The Callable hint, without or without signature parameters
            value: The value to check
            
        Returns:
            bool: True if value is callable with the specified signature
        """
        if not callable(value):
            return False
        
        args=get_args(hint)

        # If no arguments provided (plain Callable), accept any callable
        if not args:
            return True

        # Callable should have exactly two arguments: parameter types and return type
        if len(args) != 2:
            raise TypeCheckError(f"Callable requires 2 arguments, got {len(args)}")

        arg_types, return_type = args

        # Handle Callable[..., X] case (ellipsis means any arguments)
        if arg_types is ...:
            # We can't reliably check the signature but can check return annotation
            try:
                sig = inspect.signature(value)
                actual_return = sig.return_annotation
                
                # If function doesn't specify return type, accept it
                if actual_return == inspect.Parameter.empty:
                    return True
                    
                # Otherwise check if return type is compatible
                return self._compare_type_annotations(actual_return, return_type)
            except (ValueError, TypeError):
                # If we can't get the signature, be lenient
                return True

        # For regular Callable[[arg_types], return_type], check parameters and return
        try:
            sig = inspect.signature(value)
        except (ValueError, TypeError):
            # Can't inspect the function, be lenient
            return True

        # Get relevant parameters (skip *args, **kwargs)
        params = [
            p for p in sig.parameters.values()
            if p.kind in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY
            )
        ]

        # Check number of parameters matches
        if len(params) != len(arg_types):
            return False

        # Check each parameter type if annotation is present
        for i, (param, expected_type) in enumerate(zip(params, arg_types)):
            if param.annotation != inspect.Parameter.empty:
                # If parameter is annotated, check it matches expected type
                if not self._compare_type_annotations(param.annotation, expected_type):
                    return False

        # Check return type if annotation is present
        actual_return = sig.return_annotation
        if actual_return != inspect.Parameter.empty:
            if not self._compare_type_annotations(actual_return, return_type):
                return False

        return True

    def _compare_type_annotations(self, actual, expected):
        """
        Compare two type annotations for compatibility.
        Used primarily for checking Callable parameter and return types.
        
        Args:
            actual: The actual type annotation
            expected: The expected type annotation
            
        Returns:
            bool: True if the actual type is compatible with the expected type
        """
        # Special case: If actual is empty annotation, we can't verify it
        if actual is expected:
            return True
        
        if actual in (None,type(None)) and expected in (None,type(None)) :
            return True

        if actual == inspect.Parameter.empty:
            return True
            
        # If expected is Any, accept any type
        if expected == Any:
            return True
            
        # Use our existing type checking logic
        try:
            # Create a dummy value of the actual type to check against expected
            if isinstance(actual, type):
                dummy = actual()  # This won't work for all types
                return self._check_type_internal(expected, dummy)
        except:
            pass
            
        # Fall back to checking type compatibility directly
        try:
            return issubclass(actual, expected)
        except TypeError:
            # Handle non-class types (like Union, Optional etc)
            return actual == expected

    def _check_protocol(self, hint, value):
        """
        Check if a value implements a Protocol.
        
        Args:
            hint: A Protocol type (must be runtime_checkable for isinstance checks)
            value: The value to check
            
        Returns:
            bool: True if value implements the Protocol
        """
        # For runtime_checkable protocols, we can use isinstance directly
        if getattr(hint, "_is_runtime_protocol", False):
            return isinstance(value, hint)
            
        # Otherwise, we need to check structural compatibility
        protocol_attrs = {}
        
        # Collect all attributes from the Protocol and its bases
        for base in getattr(hint, '__mro__', [hint]):
            if base is typing.Protocol or base is object:
                continue
                
            # Get annotated attributes (including special methods)
            if hasattr(base, '__annotations__'):
                for name, expected_type in base.__annotations__.items():
                    protocol_attrs[name] = expected_type
                    
            # Get non-annotated but required methods/properties
            for name, attr in getattr(base, '__dict__', {}).items():
                # Skip private attributes, but include dunder methods
                if name.startswith('_') and not (name.startswith('__') and name.endswith('__')):
                    continue
                    
                if isinstance(attr, property):
                    # For properties, check if they exist in value
                    if name not in protocol_attrs:
                        protocol_attrs[name] = Any
                elif callable(attr) and not isinstance(attr, type):
                    # For methods, just check they exist and are callable
                    if name not in protocol_attrs:
                        protocol_attrs[name] = Callable

        # Check all required attributes and methods
        for name, expected_type in protocol_attrs.items():
            # Check if attribute exists (including special methods)
            if not hasattr(value, name):
                return False
                
            # If expected type is Callable, verify attribute is callable
            if expected_type is Callable:
                if not callable(getattr(value, name)):
                    return False
                continue
                    
            # For non-callable attributes that have type annotations, 
            # check their type matches
            if expected_type is not Any:
                attr_value = getattr(value, name)
                if not self._check_type_internal(expected_type, attr_value):
                    return False
                    
        return True
    #endregion

    #region: Utilities

    def _resolve_forward_ref(self, hint: str, frame) -> Any:
        """
        Resolve a forward reference string to an actual type.
        Searches progressively wider scopes starting from the local frame.
        
        Args:
            hint: A string representing a forward reference type
            frame: The execution frame to start resolution from
            
        Returns:
            The resolved type
            
        Raises:
            TypeCheckError: If the forward reference cannot be resolved
        """
        # Try progressively wider scopes
        while frame:
            try:
                # Try locals first
                if frame.f_locals:
                    return eval(hint, frame.f_globals, frame.f_locals)
                # Then try globals
                return eval(hint, frame.f_globals)
            except (NameError, AttributeError):
                frame = frame.f_back
                
        raise TypeCheckError(f"Could not resolve forward reference: {hint}")

    #endregion

#endregion

#region: Coercer Class

class Coercer:
    """
    Système de coercion intelligent basé sur le TypeChecker existant.
    Utilise l'analyse de types pour déterminer les coercions possibles.
    """
    
    def __init__(self, type_checker: TypeChecker):
        self.type_checker = type_checker
        self._coercion_strategies = self._build_coercion_strategies()
    
    def coerce(self, value: Any, target_hint: Any) -> Any:
        """
        Point d'entrée principal : tente de coercer value vers target_hint.
        """
        # Si déjà compatible, pas de coercion
        try:
            if self.type_checker.check_type(target_hint, value):
                return value
        except (TypeMismatchError, TypeCheckError):
            pass
        
        # Sinon, tentative de coercion intelligente
        return self._attempt_smart_coercion(value, target_hint)
    
    def _attempt_smart_coercion(self, value: Any, target_hint: Any) -> Any:
        """
        🔥 Coercion intelligente basée sur l'analyse du TypeChecker.
        """
        # Utiliser l'intelligence du TypeChecker pour analyser le type cible
        if self.type_checker._is_special_form(target_hint):
            return self._coerce_special_form(value, target_hint)
        elif self.type_checker._is_generic_alias(target_hint):
            return self._coerce_generic_alias(value, target_hint)
        elif self.type_checker._is_basic_type(target_hint):
            return self._coerce_basic_type(value, target_hint)
        elif isinstance(target_hint, TypeVar):
            return self._coerce_typevar(value, target_hint)
        else:
            # Fallback vers coercions standards
            return self._fallback_coercion(value, target_hint)
            
    def _coerce_special_form(self, value: Any, target_hint: Any) -> Any:
        """
        Coercion pour Union, Optional, Literal, etc.
        Réutilise la logique d'analyse du TypeChecker !
        """
        form_name = self.type_checker._get_special_form_name(target_hint)
        
        if form_name == 'Union':
            return self._coerce_union(value, target_hint)
        elif form_name == 'Optional':
            return self._coerce_optional(value, target_hint)
        elif form_name == 'Literal':
            return self._coerce_literal(value, target_hint)
        elif form_name == 'Final':
            args = get_args(target_hint)
            if args:
                return self.coerce(value, args[0])  # Récursion !
            return value
        else:
            raise CoercionError(f"Cannot coerce to special form: {form_name}")
        
    def _coerce_union(self, value: Any, target_hint: Any) -> Any:
        """
        Union: essaie chaque type dans l'ordre, retourne le premier qui marche.
        """
        args = get_args(target_hint)
        
        # Stratégie intelligente : d'abord les types "exacts", puis les coercions
        for union_type in args:
            try:
                # D'abord vérifier si déjà compatible
                if self.type_checker.check_type(union_type, value):
                    return value
            except (TypeMismatchError, TypeCheckError):
                continue
        
        # Sinon, tenter les coercions
        for union_type in args:
            try:
                coerced = self.coerce(value, union_type)  # Récursion intelligente !
                # Valider que la coercion a marché
                if self.type_checker.check_type(union_type, coerced):
                    return coerced
            except (CoercionError, TypeMismatchError):
                continue
        
        raise CoercionError(f"Cannot coerce {type(value)} to any type in {target_hint}")

    def _coerce_optional(self, value: Any, target_hint: Any) -> Any:
        """
        Optional[T] = Union[T, None] - délègue à Union !
        """
        if value is None:
            return None
        
        args = get_args(target_hint)
        if not args:
            raise CoercionError("Optional requires exactly 1 type argument")
        
        return self.coerce(value, args[0])  # Récursion vers T
    
    def _coerce_literal(self, value: Any, target_hint: Any) -> Any:
        """
        Literal[val1, val2, ...] : la valeur doit être exactement une des valeurs littérales.
        """
        args = get_args(target_hint)
        if value in args:
            return value
        
        # Tentative de coercion intelligente vers chaque valeur littérale
        for literal_val in args:
            try:
                # Si c'est le même type, essayer une conversion directe
                if type(value) != type(literal_val):
                    if isinstance(literal_val, (int, float, str, bool)):
                        coerced = self._coerce_basic_type(value, type(literal_val))
                        if coerced == literal_val:
                            return coerced
            except CoercionError:
                continue
        
        raise CoercionError(f"Cannot coerce {value!r} to any literal value in {args}")
    
    def _coerce_generic_alias(self, value: Any, target_hint: Any) -> Any:
        """
        List[int], Dict[str, float], etc.
        Réutilise la logique des checkers existants !
        """
        origin = get_origin(target_hint)
        args = get_args(target_hint)
        
        # Utiliser l'intelligence du TypeChecker pour identifier le checker approprié
        checker = self.type_checker._get_checker(origin)
        
        if checker == self.type_checker._check_sequence_like:
            return self._coerce_sequence_like(value, target_hint, origin, args)
        elif checker == self.type_checker._check_mapping_like:
            return self._coerce_mapping_like(value, target_hint, origin, args)
        elif checker == self.type_checker._check_set_like:
            return self._coerce_set_like(value, target_hint, origin, args)
        elif checker == self.type_checker._check_tuple_like:
            return self._coerce_tuple_like(value, target_hint, origin, args)
        else:
            # Utiliser l'ABC checker si disponible
            abc_checker = self.type_checker._get_abc_checker(origin)
            if abc_checker:
                return self._coerce_with_abc_checker(value, target_hint, origin, args)
            
            raise CoercionError(f"No coercion strategy for {target_hint}")

    def _coerce_sequence_like(self, value: Any, target_hint: Any, origin: Any, args: Tuple) -> Any:
        """
        Coercion pour List[T], Sequence[T], etc.
        """
        # D'abord, convertir vers le type de conteneur approprié
        target_type = self.type_checker._origin_to_type(origin)
        
        # Convertir la valeur vers le type de séquence cible
        if isinstance(value, str):
            # String -> List : traitement spécial
            if target_type in (list, collections.abc.Sequence):
                converted = list(value)  # "abc" -> ['a', 'b', 'c']
            else:
                raise CoercionError(f"Cannot coerce string to {target_type}")
        elif hasattr(value, '__iter__') and not isinstance(value, (str, bytes)):
            # Convertir iterable -> type cible
            if target_type == list:
                converted = list(value)
            elif target_type == tuple:
                converted = tuple(value)
            elif target_type == set:
                converted = set(value)
            else:
                # Pour les ABC, essayer de créer le type d'origine
                try:
                    converted = origin(value)
                except:
                    converted = list(value)  # Fallback vers list
        else:
            raise CoercionError(f"Cannot coerce {type(value)} to sequence")
        
        # Si on a un type d'élément spécifié, coercer récursivement
        if args and len(args) == 1:
            elem_type = args[0]
            coerced_elements = []
            for item in converted:
                coerced_item = self.coerce(item, elem_type)  # 🔥 Récursion intelligente !
                coerced_elements.append(coerced_item)
            
            # Reconstruire le bon type
            if target_type == list:
                return coerced_elements
            elif target_type == tuple:
                return tuple(coerced_elements)
            elif target_type == set:
                return set(coerced_elements)
            else:
                try:
                    return origin(coerced_elements)
                except:
                    return coerced_elements
        
        return converted

    def _coerce_mapping_like(self, value: Any, target_hint: Any, origin: Any, args: Tuple) -> Any:
        """
        Coercion pour Dict[K, V], Mapping[K, V], etc.
        """
        target_type = self.type_checker._origin_to_type(origin)
        
        # Convertir vers dict-like
        if hasattr(value, 'items'):
            converted = dict(value.items())
        elif hasattr(value, '__iter__'):
            # Essayer de convertir depuis une séquence de paires
            try:
                converted = dict(value)
            except (ValueError, TypeError):
                raise CoercionError(f"Cannot coerce {type(value)} to mapping")
        else:
            raise CoercionError(f"Cannot coerce {type(value)} to mapping")
        
        # Coercer les clés et valeurs si types spécifiés
        if args and len(args) == 2:
            key_type, value_type = args
            coerced_dict = {}
            
            for k, v in converted.items():
                coerced_key = self.coerce(k, key_type)     # 🔥 Récursion !
                coerced_val = self.coerce(v, value_type)   # 🔥 Récursion !
                coerced_dict[coerced_key] = coerced_val
            
            converted = coerced_dict
        
        # Créer le bon type final
        if target_type == dict:
            return converted
        else:
            try:
                return origin(converted)
            except:
                return converted

    def _coerce_set_like(self, value: Any, target_hint: Any, origin: Any, args: Tuple) -> Any:
        """
        Coercion pour Set[T], FrozenSet[T], etc.
        """
        target_type = self.type_checker._origin_to_type(origin)
        
        # Convertir vers set-like
        if isinstance(value, str):
            # String -> Set de chars
            converted = set(value)
        elif hasattr(value, '__iter__'):
            # Convertir iterable -> set
            converted = set(value)
        else:
            raise CoercionError(f"Cannot coerce {type(value)} to set")
        
        # Si on a un type d'élément spécifié, coercer récursivement
        if args and len(args) == 1:
            elem_type = args[0]
            coerced_elements = set()
            for item in converted:
                coerced_item = self.coerce(item, elem_type)  # 🔥 Récursion !
                coerced_elements.add(coerced_item)
            converted = coerced_elements
        
        # Créer le bon type final
        if target_type == set:
            return converted
        elif target_type == frozenset:
            return frozenset(converted)
        else:
            try:
                return origin(converted)
            except:
                return converted

    def _coerce_tuple_like(self, value: Any, target_hint: Any, origin: Any, args: Tuple) -> Any:
        """
        Coercion pour Tuple avec gestion des cas spéciaux.
        Tuple[int, str, bool] vs Tuple[int, ...] vs Tuple[()]
        """
        target_type = self.type_checker._origin_to_type(origin)
        
        # Convertir vers iterable d'abord
        if isinstance(value, str):
            converted = tuple(value)  # "abc" -> ('a', 'b', 'c')
        elif hasattr(value, '__iter__'):
            converted = tuple(value)
        else:
            raise CoercionError(f"Cannot coerce {type(value)} to tuple")
        
        # Gestion des cas spéciaux de tuple
        if not args:
            # Tuple sans args = Tuple[Any, ...]
            return converted
        
        # Tuple vide - Tuple[()]
        if len(args) == 1 and args[0] == ():
            if len(converted) == 0:
                return converted
            else:
                raise CoercionError(f"Expected empty tuple, got {len(converted)} elements")
        
        # Tuple homogène - Tuple[int, ...]
        if len(args) == 2 and args[1] is ...:
            elem_type = args[0]
            coerced_elements = []
            for item in converted:
                coerced_item = self.coerce(item, elem_type)
                coerced_elements.append(coerced_item)
            return tuple(coerced_elements)
        
        # Tuple hétérogène - Tuple[int, str, bool]
        if len(converted) != len(args):
            raise CoercionError(f"Expected tuple of length {len(args)}, got {len(converted)}")
        
        coerced_elements = []
        for i, (item, expected_type) in enumerate(zip(converted, args)):
            coerced_item = self.coerce(item, expected_type)
            coerced_elements.append(coerced_item)
        
        return tuple(coerced_elements)

    def _coerce_with_abc_checker(self, value: Any, target_hint: Any, origin: Any, args: Tuple) -> Any:
        """
        Coercion pour types custom qui héritent d'ABC.
        """
        # Stratégie : essayer de créer le type d'origine avec la valeur
        try:
            if hasattr(value, '__iter__') and not isinstance(value, (str, bytes)):
                return origin(value)
            else:
                return origin([value])  # Wrap en liste si pas iterable
        except:
            raise CoercionError(f"Cannot coerce {type(value)} to {origin}")

    def _coerce_basic_type(self, value: Any, target_hint: Any) -> Any:
        """
        Coercion rapide pour types basiques avec stratégies optimisées.
        """
        # Utiliser les stratégies pré-calculées
        coercion_key = (type(value), target_hint)
        
        if coercion_key in self._coercion_strategies:
            strategy = self._coercion_strategies[coercion_key]
            try:
                result = strategy(value)
                if result is not None:  # Strategy peut retourner None si impossible
                    return result
            except:
                pass
        
        # Fallback vers stratégies plus génériques
        return self._generic_basic_coercion(value, target_hint)

    def _coerce_typevar(self, value: Any, target_hint: TypeVar) -> Any:
        """
        Coercion pour TypeVar avec contraintes/bounds.
        """
        # Si TypeVar a des contraintes, essayer de coercer vers chacune
        if target_hint.__constraints__:
            for constraint in target_hint.__constraints__:
                try:
                    return self.coerce(value, constraint)
                except CoercionError:
                    continue
            raise CoercionError(f"Cannot coerce {type(value)} to any constraint of {target_hint}")
        
        # Si TypeVar a un bound, coercer vers le bound
        if target_hint.__bound__:
            return self.coerce(value, target_hint.__bound__)
        
        # Sinon, accepter la valeur telle quelle (comme Any)
        return value

    def _fallback_coercion(self, value: Any, target_hint: Any) -> Any:
        """
        Coercion de dernier recours pour types non reconnus.
        """
        # Essayer isinstance comme dernière chance
        if isinstance(target_hint, type):
            try:
                return target_hint(value)
            except:
                pass
        
        raise CoercionError(f"No coercion strategy available for {target_hint}")

    def _build_coercion_strategies(self) -> Dict[Tuple[type, type], Callable]:
        """
        🔥 Stratégies de coercion optimisées pour cas courants.
        """
        return {
            # String vers numerics
            (str, int): self._str_to_int,
            (str, float): self._str_to_float,
            (str, bool): self._str_to_bool,
            
            # Numerics vers string
            (int, str): str,
            (float, str): str,
            (bool, str): str,
            
            # Conversions numeriques
            (int, float): float,
            (float, int): self._float_to_int,
            (bool, int): int,  # True -> 1, False -> 0
            (int, bool): bool, # 0 -> False, else -> True
            
            # Containers basiques
            (tuple, list): list,
            (list, tuple): tuple,
            (set, list): list,
            (list, set): set,
            (frozenset, set): set,
            (set, frozenset): frozenset,
            
            # String vers containers
            (str, list): list,  # "abc" -> ['a', 'b', 'c']
            (str, tuple): tuple,
            (str, set): set,
        }

    def _str_to_int(self, value: str) -> int:
        """Conversion string -> int avec gestion d'erreurs."""
        value = value.strip()
        if not value:
            raise CoercionError("Empty string cannot be converted to int")
        
        # Gérer les cas comme "123.0" -> 123
        try:
            if '.' in value:
                float_val = float(value)
                if float_val.is_integer():
                    return int(float_val)
                else:
                    raise CoercionError(f"String '{value}' represents a non-integer float")
            return int(value)
        except ValueError as e:
            raise CoercionError(f"Cannot convert '{value}' to int: {e}")

    def _str_to_float(self, value: str) -> float:
        """Conversion string -> float avec gestion d'erreurs."""
        value = value.strip()
        if not value:
            raise CoercionError("Empty string cannot be converted to float")
        
        try:
            return float(value)
        except ValueError as e:
            raise CoercionError(f"Cannot convert '{value}' to float: {e}")

    def _str_to_bool(self, value: str) -> bool:
        """Conversion string -> bool avec logique intelligente."""
        value = value.strip().lower()
        
        # Valeurs truthy
        if value in ('true', '1', 'yes', 'on', 'y', 't'):
            return True
        # Valeurs falsy
        elif value in ('false', '0', 'no', 'off', 'n', 'f', ''):
            return False
        else:
            raise CoercionError(f"Cannot convert '{value}' to bool")

    def _float_to_int(self, value: float) -> int:
        """Conversion float -> int seulement si pas de partie décimale."""
        if value.is_integer():
            return int(value)
        else:
            raise CoercionError(f"Float {value} has decimal part, cannot convert to int")

    def _generic_basic_coercion(self, value: Any, target_hint: Any) -> Any:
        """
        Coercion générique pour types basiques non couverts par les stratégies.
        """
        if isinstance(target_hint, type):
            try:
                # Tentative de construction directe
                return target_hint(value)
            except:
                raise CoercionError(f"Cannot coerce {type(value)} to {target_hint}")
        
        raise CoercionError(f"Cannot coerce {type(value)} to {target_hint}")

#endregion

#region: Public API

_global_coercer = None
_global_typechecker=None

def _get_global_typechecker() -> TypeChecker:
    """
    Obtient l'instance globale du typechecker (avec lazy initialization).
    Utilisé par la fonction utilitaire check_type() et le décorateur typechecked(func).
    """
    global _global_typechecker
    if _global_typechecker is None:
        _global_typechecker = TypeChecker()
    return _global_typechecker

def _get_global_coercer() -> Coercer:
    """
    Obtient l'instance globale du coercer (avec lazy initialization).
    Utilisé par la fonction utilitaire coerce().
    """
    global _global_coercer
    if _global_coercer is None:
        _global_coercer = Coercer(_get_global_typechecker())
    return _global_coercer

def reset_global_typechecker():
    """
    🔄 Reset l'instance globale du typechecker.
    Utile pour les tests ou si on veut forcer une réinitialisation.
    """
    global _global_typechecker
    _global_typechecker = None

def reset_global_coercer():
    """
    🔄 Reset l'instance globale du coercer.
    Utile pour les tests ou si on veut forcer une réinitialisation.
    """
    global _global_coercer
    _global_coercer = None

def coerce(value: Any, hint: Any) -> Any:
    """
    🚀 Fonction utilitaire simple pour coercer une valeur vers un type.
    
    Args:
        value: La valeur à coercer
        hint: Le type hint cible (int, List[str], Union[int, str], etc.)
        
    Returns:
        La valeur coercée vers le type cible
        
    Raises:
        CoercionError: Si la coercion n'est pas possible
        
    Examples:
        >>> from adict import coerce
        >>> coerce("42", int)
        42
        >>> coerce(("a", "b"), List[str])  
        ['a', 'b']
        >>> coerce("123.45", Union[int, float])
        123.45
        >>> coerce([("key", "value")], Dict[str, str])
        {'key': 'value'}
    """
    return _get_global_coercer().coerce(value, hint)

def can_coerce(value: Any, hint: Any) -> bool:
    """
    🔍 Vérifie si une valeur peut être coercée vers un type sans faire la coercion.
    
    Args:
        value: La valeur à tester
        hint: Le type hint cible
        
    Returns:
        True si la coercion est possible, False sinon
        
    Examples:
        >>> can_coerce("42", int)
        True
        >>> can_coerce("abc", int)
        False
        >>> can_coerce([1, 2, 3], List[str])
        True  # Chaque int peut être coercé en str
    """
    try:
        _get_global_coercer().coerce(value, hint)
        return True
    except CoercionError:
        return False


def check_type(hint: Any, value: Any) -> bool:
    """
    Convenience function to check if a value matches a type hint.
    
    Args:
        hint: A type annotation or typing construct
        value: The value to check against the type hint
        
    Returns:
        bool: True if the value matches the type hint
        
    Raises:
        TypeMismatchError: When the value doesn't match the type hint
        TypeCheckError: When there was an error during the type check
    """

    return _get_global_typechecker().check_type(hint, value)


# Decorator for runtime type checking
def typechecked(func):
    """
    Decorator to add runtime type checking to a function.
    
    Example:
        @typechecked
        def add(a: int, b: int) -> int:
            return a + b
    """
    if not hasattr(func, "__annotations__"):
        return func
        
    signature = inspect.signature(func)
    checker = _get_global_typechecker()
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Bind arguments to the signature
        bound_args = signature.bind(*args, **kwargs)
        bound_args.apply_defaults()
        
        # Check argument types
        for param_name, param in signature.parameters.items():
            if param_name in func.__annotations__:
                expected_type = func.__annotations__[param_name]
                arg_value = bound_args.arguments[param_name]
                
                # Special handling for *args parameter
                if param.kind == inspect.Parameter.VAR_POSITIONAL:
                    # Check each item in the *args tuple
                    for item in arg_value:
                        if not checker.check_type(expected_type, item):
                            raise TypeMismatchError(
                                f"Argument '{param_name}' has invalid item: "
                                f"expected {expected_type}, got {type(item)}"
                            )
                # Special handling for **kwargs parameter
                elif param.kind == inspect.Parameter.VAR_KEYWORD:
                    # Check each value in the **kwargs dict
                    for key, item in arg_value.items():
                        if not checker.check_type(expected_type, item):
                            raise TypeMismatchError(
                                f"Argument '{param_name}[{key}]' has invalid type: "
                                f"expected {expected_type}, got {type(item)}"
                            )
                # Normal parameter
                else:
                    if not checker.check_type(expected_type, arg_value):
                        raise TypeMismatchError(
                            f"Argument '{param_name}' has invalid type: "
                            f"expected {expected_type}, got {type(arg_value)}"
                        )
        
        # Call the function
        result = func(*args, **kwargs)
        
        # Check return type
        if "return" in func.__annotations__:
            return_type = func.__annotations__["return"]
            if not checker.check_type(return_type, result):
                raise TypeMismatchError(
                    f"Return value has invalid type: "
                    f"expected {return_type}, got {type(result)}"
                )
        
        return result
    
    return wrapper
#endregion