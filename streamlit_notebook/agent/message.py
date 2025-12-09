from modict import modict
from .utils import short_id, timestamp, format
from textwrap import dedent

class MessageChunk(modict):

    content = ''
    reasoning = ''
    tool_calls=None

    @classmethod
    def from_delta(cls,delta):
        return cls(modict(delta.model_dump()).extract('content','reasoning','tool_calls'))

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

    def get_tool_call_by_index(self,index):
        for tc in self.get('tool_calls',[]):
            if tc.get('index')==index:
                return tc
        return None

    def add_chunk(self,msg_chunk:'MessageChunk'):
        self.content+=msg_chunk.get('content') or ''
        self.reasoning+=msg_chunk.get('reasoning') or ''
        tool_calls_chunk=msg_chunk.get('tool_calls')
        if tool_calls_chunk:
            for tc in tool_calls_chunk:
                existing_tc=self.get_tool_call_by_index(tc.index)
                if existing_tc is None:
                    self.setdefault('tool_calls',[]).append(tc)
                else:
                    #agregate function arguments
                    args_chunk=tc.get('function',{}).get('arguments','')
                    existing_tc.function.arguments+=args_chunk

    def as_string(self):
        params=' '.join(f"{k}={v!r}" for k,v in self.extract('name','role','type','timestamp').items())
        content=str(self.get('content') or '')
        return dedent(
        f"""<Message {params}>
        {content}
        </Message>"""
        )
    
