"""Contains WebRTC-related message definitions."""

from typing import Literal
from pydantic import BaseModel, PositiveInt, model_validator

from aiortc.rtcicetransport import RTCIceCandidate

MessageType = Literal["error", "register", "registered", "offer", "pranswer", "answer", "rollback", "ice-candidate", "close-connection"]


class WebRTCSignalMessage(BaseModel):
    """Base class for WebRTC signaling messages."""

    type: MessageType
    version: PositiveInt


class ErrorMessage(WebRTCSignalMessage):
    """Message for signaling errors."""

    type  = "error"
    message: str


class RegisterMessage(WebRTCSignalMessage):
    """Message for registering a new WebRTC connection."""

    type = "register"
    server_id: str
    mic_stream_count: PositiveInt
    cam_stream_count: PositiveInt
    accept_output_streams: bool
    roles: Literal["ingest", "observer", "output", "ingest-output"]


class RegisteredMessage(WebRTCSignalMessage):
    """Message confirming successful registration."""

    type = "registered"
    server_id: str


class RTCSessionDescriptionMessage(WebRTCSignalMessage):
    """Message for WebRTC session descriptions (offer/answer)."""

    sdp: str

    @model_validator(mode="after")
    def check_sdp_type(cls, values):
        sdp_type = values.get("type")
        if sdp_type not in {"offer", "answer", "pranswer", "rollback"}:
            raise ValueError(f"Invalid SDP type: {sdp_type}")
        return cls

class ICECandidateMessage(WebRTCSignalMessage):
    """Message for ICE candidates."""

    type = "ice-candidate"
    data: RTCIceCandidate

class CloseConnectionMessage(WebRTCSignalMessage):
    """Message to close a WebRTC connection."""

    type = "close-connection"
    reason: str
