from modict import modict
from .utils import short_id, timestamp, format
from textwrap import dedent

class Message(modict):

    content=''
    role="assistant"
    name=''
    reasoning=''
    type="message"
    id=modict.factory(lambda :short_id())
    session_id=None
    timestamp=modict.factory(lambda : timestamp())
    lasting=0
    embedding=None

    def format(self,context=None):
        if self.type=="image":
            return self
        else:
            msg=Message(**self)
            msg.content=format(msg.content,context=context)
            return msg
        
    def to_llm_client_format(self, include_name=True):
        name=f"{self.name}:{self.timestamp!r}"
        msg=self.extract('role','content','tool_calls','tool_call_id')
        if include_name and self.name:
            msg['name']=name
        return msg

    def as_string(self):
        params=' '.join(f"{k}={v!r}" for k,v in self.extract('name','role','type','timestamp').items())
        content=str(self.get('content') or '')
        return dedent(
        f"""<Message {params}>
        {content}
        </Message>"""
        )
    
