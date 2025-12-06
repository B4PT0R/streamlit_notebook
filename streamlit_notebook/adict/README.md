# adict - The Swiss Army Knife of Python Data Structures

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**adict** is a sophisticated, hybrid data structure that combines the simplicity of Python dictionaries with the power of dataclasses and the robustness of Pydantic models. It's designed to be the versatile tool you'll want to use in every project for handling structured data.

## 🎯 Philosophy & Goals

adict bridges the gap between different Python data paradigms:

- **📚 Dict-like**: Native dictionary inheritance with full compatibility
- **🏗️ Dataclass-like**: Type annotations and structured field definitions  
- **🛡️ Pydantic-like**: Runtime validation, type coercion, and computed properties
- **🔧 Developer-friendly**: Intuitive API that "just works" for common patterns

### Why adict?

```python
# Traditional approaches require choosing between flexibility and structure
data = {"name": "Alice", "age": 30}           # Dict: flexible but unstructured

@dataclass
class User: name: str; age: int               # Dataclass: structured but rigid

class User(BaseModel): name: str; age: int    # Pydantic: powerful but heavy

# adict: Best of all worlds
class User(adict):
    name: str
    age: int = 25

user = User(name="Alice")                   # ✅ Structured
user.age                                    # 25 ✅ Default value
user.email = "alice@email.com"              # ✅ Flexible  
user['phone'] = "123-456-7890"              # ✅ Dict-compatible
isinstance(user,dict)                       # True (still a dict!)
```

## 🚀 Key Features

### Core Capabilities
- **Full dict inheritance** - All native dict methods work seamlessly. adicts ARE dicts!
- **Attribute-style access** - `obj.key` and `obj['key']` both work
- **Type annotations** - Optional type hints with runtime validation
- **Recursive conversion** - Nested dicts automatically become adicts
- **JSON-first design** - Built-in JSON serialization/deserialization
- **Path-based access** - Access nested structures with dot notation

### Advanced Features
- **Computed properties** - Dynamic values with dependency tracking
- **Custom validators** - Field-level validation and transformation
- **Type coercion** - Intelligent type conversion system
- **Deep operations** - Merge, diff, walk through nested structures
- **Field extraction** - Select/exclude keys with simple methods

## 📦 Installation

```bash
pip install adict
```

## 🏃‍♂️ Quick Start

### Basic Usage

```python
from adict import adict

# Create from dict or keyword arguments
user = adict({"name": "Alice", "age": 30})
user = adict(name="Alice", age=30)

# Attribute and dict-style access
print(user.name)        # "Alice"
print(user['age'])      # 30

# Add new fields dynamically
user.email = "alice@email.com"
user['phone'] = "123-456-7890"
```

### Structured Classes

```python
from adict import adict
from typing import List, Optional

class User(adict):
    name: str
    age: int = 25
    email: Optional[str] = None
    tags: List[str] = adict.factory(list)  # Factory for mutable defaults

# Type-safe creation
user = User(name="Bob", age=35)
print(user.age)         # 35
print(user.tags)        # []
```

### Nested Structures & Path Access

```python
# Automatic recursive conversion
data = adict({
    "user": {"name": "Alice", "profile": {"city": "Paris"}},
    "settings": {"theme": "dark"}
})

# Path-based access
print(data.get_nested("user.name"))              # "Alice"
data.set_nested("user.profile.country", "France")
print(data.has_nested("settings.theme"))         # True

# Attribute access works too
print(data.user.profile.city)                    # "Paris"
```

## 💫 Advanced Features

### Computed Properties

```python
class Calculator(adict):
    a: float = 0
    b: float = 0
    
    @adict.computed(cache=True, deps=['a', 'b'])
    def sum_ab(self):
        print("Computing sum...")
        return self.a + self.b
    
    @adict.computed(cache=True, deps=['sum_ab'])  # Cascading dependencies
    def doubled_sum(self):
        return self.sum_ab * 2

calc = Calculator(a=10, b=20)
print(calc.sum_ab)         # "Computing sum..." → 30
print(calc.sum_ab)         # 30 (cached)
calc.a = 15                # Invalidates cache automatically
print(calc.sum_ab)         # "Computing sum..." → 35
print(calc.doubled_sum)    # 70
```

### Custom Validators

```python
class Profile(adict):
    email: str
    age: int
    
    @adict.check('email')
    def validate_email(self, value):
        """Clean and validate email addresses"""
        email = value.lower().strip()
        if '@' not in email:
            raise ValueError("Invalid email format")
        return email
    
    @adict.check('age')  
    def validate_age(self, value):
        """Ensure age is reasonable"""
        age = int(value)
        if age < 0 or age > 150:
            raise ValueError("Invalid age range")
        return age

profile = Profile(email="  ALICE@EMAIL.COM  ", age="30")
print(profile.email)  # "alice@email.com" (cleaned)
print(profile.age)    # 30 (converted to int)
```

### Deep Operations

```python
# Deep merging
network_config = adict({"db": {"host": "localhost", "port": 5432}})
overrides = {"db": {"port": 3306, "ssl": True}}
network_config.merge(overrides)
# Result: {"db": {"host": "localhost", "port": 3306, "ssl": True}}

# Walking through nested structures
data = adict({"users": [{"name": "Alice"}, {"name": "Bob"}]})
for path, value in data.walk():
    print(f"{path}: {value}")
# Output:
# users.0.name: Alice
# users.1.name: Bob

# Flattened view
flat = data.walked()  # {"users.0.name": "Alice", "users.1.name": "Bob"}
```

## 🛠️ Configuration Options

`adict.config` allows you to customize the behavior of your adict subclass.
It returns an `AdictConfig` object (dataclass) that you may pass as the `_config` class variable.

```python
class MyAdict(adict):
    _config = adict.config(
        strict=False,               # Strict runtime type checking
        coerce=False,               # Enable automatic type coercion
        allow_extra=True,           # Disallow extra attributes
        enforce_json=False,         # Enforce JSON serializability of values
    )
```

Subclass configs are properly merged with parent class configs, also supporting multiple inheritance patterns (following MRO order).

```python
class Parent(adict):
    _config = adict.config(strict=True, coerce=False)

class Child(Parent):
    _config = adict.config(coerce=True)  # strict=True, coerce=True (overrides Parent)

class A(adict):
    _config = adict.config(strict=True)
    a: int=1
    value: str="A"

class B(adict):
    _config = adict.config(strict=False, coerce=True)
    b: int=2
    value: str="B"

class C(A,B):
    _config = adict.config(allow_extra=False) 
    # strict=True from A (A overrides B, since A follows B in MRO), 
    # coerce=True from B
    # allow_extra=False from C

c = C()
print(c.a) # 1
print(c.b) # 2
print(c.value) # "A" (A overrides B)
c.a = "3"
print(c.a) # 3 (coercion enabled)

try:
    c.a = "invalid" 
except Exception as e:
    print(e) # ❌ TypeError (strict mode enabled)

try:
    c.undefined = "value" 
except Exception as e:
    print(e) # ❌ KeyError (extra fields not allowed)
```

### Example

```python
class StrictConfig(adict):

    _config=adict.config(
        strict = True          # Enable runtime type checking
        allow_extra = False    # Disallow undefined fields
        coerce = True          # Enable type coercion
    )

    name: str
    count: int

config = StrictConfig(name="test", count=42)
# config.undefined = "value"    # ❌ KeyError (extra fields not allowed)
# config.count = "32"           # coerced to int (coercion enabled)
# config.count = "invalid"      # ❌ TypeError (can't be coerced, type checking raises an error)
```

## 📄 JSON Integration

```python

# JSON-enforced mode
class JSONConfig(adict):

    _config=adict.config(
        enforce_json=True
    )

# Built-in JSON support
config = JSONConfig.load("config.json")        # Load from file
config = JSONConfig.loads(json_string)         # Load from string

config.dump("output.json", indent=2)          # Save to file
json_str = config.dumps(indent=2)             # Convert to string

config.data = {1, 2, 3}   # ❌ ValueError (sets are not JSON-serializable)
```

## 🎨 Field Utilities

```python
user = adict(name="Alice", age=30, email="alice@email.com", phone="123-456")

# Extract specific fields
basic_info = user.extract('name', 'age')         # {"name": "Alice", "age": 30}

# Exclude sensitive fields  
public_info = user.exclude('email', 'phone')     # {"name": "Alice", "age": 30}

# Rename fields
user.rename(email='email_address')               # Changes key name

# Deep copy
backup = user.deepcopy()
```

## 🔄 Conversion & Compatibility

```python
# Convert existing dicts to adicts (recursive)
data = {"user": {"name": "Alice"}, "count": 42}
adict_data = adict(data).to_adict()  # Deep conversion
dict_data = adict_data.to_dict()     # Back to plain dicts

# Factory method for clean conversion
converted = adict.convert(complex_nested_dict)
```

## ⚠️ Important Behaviors & Limitations

### Descriptor Handling

adict distinguishes between **definitions** and **assignments** in class namespaces:

```python
class MyAdict(adict):
    # ✅ DEFINITIONS (stay as class methods)
    @classmethod
    def my_classmethod(cls):
        return "method behavior"
    
    @property  
    def my_property(self):
        return "property behavior"
    
    # ✅ ASSIGNMENTS (become dict fields)
    external_func = some_external_function        # Stored in dict
    external_cm = classmethod(external_function)  # Stored in dict (may be non-callable)

obj = MyAdict()
obj.my_classmethod()     # ✅ Works (bound method)
obj.external_func("x")   # ✅ Works (raw function, no binding)
obj.external_cm("x")     # ❌ May fail ('classmethod' object not callable)
```

**Principle**: *Syntax determines behavior*
- `def`/`@decorator` syntax → Class behavior (Python semantics)
- `=` assignment syntax → Data storage (user responsibility)

### Import Limitations

Imports inside class namespaces are treated as field assignments:

```python
# ❌ PROBLEMATIC
class MyAdict(adict):
    import json        # Becomes a field in the dict

# ✅ RECOMMENDED  
import json
class MyAdict(adict):
    # json accessible via module scope
    pass
```

This limitation rarely affects normal usage of adict as a data structure.

### Memory Considerations

- **Validation overhead**: Type checking and coercion add runtime cost
- **Computed properties**: Cached values consume additional memory
- **Recursive conversion**: Deep nesting may impact performance

## 🆚 Comparison with Alternatives

| Feature | adict | dict | dataclass | Pydantic |
|---------|-------|------|-----------|----------|
| Dict compatibility | ✅ Full | ✅ Native | ❌ No | ❌ Limited |
| Attribute access | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes |
| Type validation | ✅ Optional | ❌ No | ❌ No | ✅ Yes |
| Runtime flexibility | ✅ High | ✅ High | ❌ Low | ❌ Medium |
| Nested structures | ✅ Auto | ❌ Manual | ❌ Manual | ✅ Auto |
| JSON integration | ✅ Built-in | ❌ Manual | ❌ Manual | ✅ Built-in |
| Learning curve | 🟡 Medium | 🟢 Low | 🟢 Low | 🔴 High |
| Performance | 🟡 Good | 🟢 Excellent | 🟢 Excellent | 🟡 Good |

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
git clone https://github.com/your-username/adict.git
cd adict
pip install -e .[dev]
pytest
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by the flexibility of Python dicts, the structure of dataclasses, and the power of Pydantic
- Built with modern Python typing and metaclass techniques
- Community feedback and real-world usage patterns

---

**adict**: *Because data structures should be both powerful and pleasant to use* 🚀