from .message import Message
import requests
import base64
import os
from io import BytesIO
import re
from PIL import Image as PILImage

def ext_to_mime(ext):
    if ext in ['jpg','jpeg']:
        return 'image/jpeg'
    elif ext in ['png']:
        return 'image/png'
    elif ext in ['webp']:
        return 'image/webp'
    elif ext in ['gif']:
        return 'image/gif'
    else:
        return None
    
def guess_mime_from_bytes(data: BytesIO):
    img = PILImage.open(data)
    format = img.format.lower()
    return f'image/{ "jpeg" if format == "jpg" else format }'
    
def get_data_url(src=None):
    if isinstance(src,str) and os.path.isfile(src):
        ext = src.split('.')[-1]
        with open(src, "rb") as image_file:
            b64 = base64.b64encode(image_file.read()).decode('utf-8')
        return f"data:{ext_to_mime(ext)};base64,{b64}"
    elif isinstance(src,BytesIO):
        if hasattr(src,'name') and isinstance(src.name,str) and '.' in src.name:
            ext = src.name.split('.')[-1].lower()
            mime_type=ext_to_mime(ext)
        else:
            mime_type=guess_mime_from_bytes(src)
        b64 = base64.b64encode(src.getvalue()).decode('utf-8')
        return f"data:{mime_type};base64,{b64}"
    elif isinstance(src,str) and src.startswith("http"):
        # Essayer de télécharger l'image
        try:
            response = requests.get(src, timeout=5)
            response.raise_for_status()
            # Trouver le mime type via Content-Type ou extension
            content_type = response.headers.get('content-type', '')
            # Fallback sur extension si header absent
            if 'image/' in content_type:
                mime_type = content_type.split(';')[0].strip()
            else:
                # Extraire l'extension depuis l'URL
                ext = src.split('.')[-1].split('?')[0]
                mime_type = ext_to_mime(ext) or 'image/jpeg'
            b64 = base64.b64encode(response.content).decode('utf-8')
            return f"data:{mime_type};base64,{b64}"
        except Exception as e:
            print(e)
            raise Exception(f"[Image] Impossible de télécharger l'image depuis {src}: {e}")
    else:
        raise Exception("No image content provided")
        

class Image(Message):

    detail="auto"
    description=None
    b64_string=None
    image_name=None
    image_path=None
    embedding=None
    name='image'
    role="system"
    type="image"

    """
    Image object suitable for AI vision implementation
    """

    def __init__(self,*args,source=None,**kwargs):
        super().__init__(*args,**kwargs)

        # If we have image_path but no b64_string, reload from file
        if self.get('image_path') and not self.get('b64_string'):
            source = self.image_path

        if not self.get('b64_string'):
            self.b64_string=self.get_data_url(source)
        if not self.get('image_name'):
            self.image_name=self.get_image_name(source)

        # Store image_path for later reload
        if not self.get('image_path') and isinstance(source, str) and os.path.isfile(source):
            self.image_path = source

    def get_data_url(self,source):
        try:
            return get_data_url(source)
        except:
            return None
        
    def get_image_name(self,source):
        if isinstance(source,BytesIO) and hasattr(source,'name') and source.name:
            return source.name
        elif source:
            return source
        return 'Unnamed image'
    
    @Message.computed(cache=True,deps=['description','detail','b64_string','image_name'])
    def content(self):
        return self.get_content()
        
    def get_content(self):
        desc=self.get('description')
        description=f"\nAlong with the following description:\n{desc}\n\n" if desc else ""
        if self.b64_string:
            content = [
                {
                    'type': 'image_url',
                    'image_url': {
                        'url': self.b64_string,
                        'detail': self.detail
                    }
                },
                {
                    'type': 'text',
                    'text': (
                        "The following image has been made available in context for visual analysis:\n"
                        + (repr(self.image_name))
                        + description
                    )
                },
            ]
        else:
            content = f"⚠️ Unable to access the image ({self.image_name!r})"
        return content
    
    def as_bytesio(self):
        """
        Return image content as file-like BytesIO object, 
        decoded from self.b64_string if available.
        """
        if self.b64_string:
            # Extraire la partie base64 du data URI
            m = re.match(r"^data:image/[^;]+;base64,(.*)$", self.b64_string)
            if m:
                raw_bytes = base64.b64decode(m.group(1))
                bio=BytesIO(raw_bytes)
                #bio.name=self.image_name
                return bio
        return None
    
    def show(self):
        """
        Affiche l'image via PIL.Image.show().
        """
        img_bytes = self.as_bytesio()
        if img_bytes:
            try:
                img = PILImage.open(img_bytes)
                img.show()
            except Exception as e:
                print(f"[Image.show] Erreur lors de l'affichage : {e}")
        else:
            print("[Image.show] Image non disponible en mémoire.")
    