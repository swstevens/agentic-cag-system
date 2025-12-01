"""
Chat interface component.
"""

from fasthtml.common import *


def chat_message(role: str, content: str) -> FT:
    """
    Render a single chat message.
    
    Args:
        role: 'user' or 'assistant'
        content: Message content
        
    Returns:
        FastHTML component
    """
    return Div(
        Div(
            P(content, cls="message-content"),
            cls=f"message message-{role}"
        ),
        cls="message-wrapper"
    )


def chat_component(messages: list) -> FT:
    """
    Render the chat interface component.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        
    Returns:
        FastHTML component
    """
    # Render message history
    message_elements = []
    if messages:
        for msg in messages:
            message_elements.append(chat_message(msg["role"], msg["content"]))
    else:
        message_elements.append(
            Div(
                P("Welcome! Ask me to build a Magic: The Gathering deck.", cls="welcome-message"),
                P("Example: 'Build me a red aggro deck for Standard'", cls="example-message"),
                cls="chat-welcome"
            )
        )
    
    # Chat history (scrollable)
    chat_history = Div(
        *message_elements,
        id="chat-history",
        cls="chat-history"
    )
    
    # Chat input form
    chat_form = Form(
        Div(
            Input(
                type="text",
                name="message",
                placeholder="Type your message...",
                required=True,
                autofocus=True,
                cls="chat-input"
            ),
            Button("Send", type="submit", cls="chat-submit"),
            cls="chat-input-group"
        ),
        hx_post="/chat",
        hx_target="#main-content",
        hx_swap="outerHTML",
        cls="chat-form"
    )
    
    return Div(
        H2("Chat", cls="chat-header"),
        chat_history,
        chat_form,
        cls="chat-container"
    )
