from modict import modict
from .utils import short_id, timestamp, format
from textwrap import dedent

class MessageChunk(modict):
    """Represents a streaming chunk of a message from the AI.

    Attributes:
        content: Text content chunk.
        reasoning: Reasoning content chunk.
        tool_calls: Tool call data chunk.
    """

    content = ''
    reasoning = ''
    tool_calls=None

    @classmethod
    def from_delta(cls,delta):
        """Create MessageChunk from OpenAI delta object.

        Args:
            delta: Delta object from OpenAI streaming response.

        Returns:
            MessageChunk instance with extracted fields.
        """
        return cls(modict(delta.model_dump()).extract('content','reasoning','tool_calls'))

class Message(modict):
    """Represents a complete message in a conversation.

    Attributes:
        content: The message text content.
        role: Role of the message sender (user, assistant, system, tool).
        name: Optional name identifier for the message sender.
        reasoning: Reasoning content for extended thinking models.
        type: Type of message (message, image, etc.).
        id: Unique identifier for the message.
        session_id: Session identifier this message belongs to.
        timestamp: Timestamp when message was created.
        lasting: Duration metric for message processing.
        embedding: Optional embedding vector for the message.
    """

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
        """Format message content with context substitution.

        Args:
            context: Optional context dictionary for template substitution.

        Returns:
            New Message instance with formatted content.
        """
        if self.type=="image":
            return self
        else:
            msg=Message(**self)
            msg.content=format(msg.content,context=context)
            return msg
        
    def to_llm_client_format(self, include_name=True):
        """Convert message to OpenAI API format.

        Args:
            include_name: Whether to include name field in output.

        Returns:
            Dictionary in OpenAI message format.
        """
        name=f"{self.name}:{self.timestamp!r}"
        msg=self.extract('role','content','tool_calls','tool_call_id')
        if include_name and self.name:
            msg['name']=name
        return msg

    def get_tool_call_by_index(self,index):
        """Retrieve a tool call by its index.

        Args:
            index: The index of the tool call to retrieve.

        Returns:
            Tool call dict or None if not found.
        """
        for tc in self.get('tool_calls',[]):
            if tc.get('index')==index:
                return tc
        return None

    def add_chunk(self,msg_chunk:'MessageChunk'):
        """Aggregate a message chunk into this message.

        Args:
            msg_chunk: MessageChunk to add to this message.
        """
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
        """Generate string representation of the message.

        Returns:
            Formatted string with message metadata and content.
        """
        params=' '.join(f"{k}={v!r}" for k,v in self.extract('name','role','type','timestamp').items())
        content=str(self.get('content') or '')
        return dedent(
        f"""<Message {params}>
        {content}
        </Message>"""
        )
    
