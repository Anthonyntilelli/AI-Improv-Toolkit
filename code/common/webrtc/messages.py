"""Contains WebRTC-related message definitions."""

from typing import Literal
from pydantic import BaseModel, PositiveInt

message_types = Literal["error", "register", "registered"]


class WebRTCSignalMessage(BaseModel):
    """Base class for WebRTC signaling messages."""

    type: message_types
    version: PositiveInt


class ErrorMessage(WebRTCSignalMessage):
    """Message for signaling errors."""

    type: message_types = "error"
    message: str


class RegisterMessage(WebRTCSignalMessage):
    """Message for registering a new WebRTC connection."""

    type: message_types = "register"
    server_id: str
    mic_stream_count: PositiveInt
    cam_stream_count: PositiveInt
    Accept_output_streams: bool
    roles: Literal["ingest", "observer", "output", "ingest-output"]


class RegisteredMessage(WebRTCSignalMessage):
    """Message confirming successful registration."""

    type: message_types = "registered"
    server_id: str


# class OfferMessage(WebRTCSignalMessage):
#     """Message for WebRTC offer."""
#     type: str = "offer"
#     data: dict

# class AnswerMessage(WebRTCSignalMessage):
#     """Message for WebRTC answer."""
#     type: str = "answer"
#     data: dict

# class IceCandidateMessage(WebRTCSignalMessage):
#     """Message for ICE candidate."""
#     type: str = "ice-candidate"
#     data: dict

# class CloseConnectionMessage(WebRTCSignalMessage):
#     """Message to close WebRTC connection."""
#     type: str = "close-connection"
#     data: dict
