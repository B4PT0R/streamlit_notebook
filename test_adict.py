from streamlit_notebook.adict import adict

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
    c.a = "invalid" # ❌ TypeError (strict mode enabled)
except Exception as e:
    print(e)

try:
    c.undefined = "value" # ❌ KeyError (extra fields not allowed)
except Exception as e:
    print(e)