"""This will be the common signaling interface for WebRTC connections using WebSockets."""

import asyncio
import base64
import binascii
import json
import secrets
import time
import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from websockets.datastructures import Headers
from websockets.asyncio.server import ServerConnection
from websockets.http11 import Request, Response
from websockets.asyncio.client import connect
import hmac
import hashlib

import pydantic

from common.webrtc.messages import ErrorMessage, RegisterMessage, RegisteredMessage

SECRET_KEY = b"potato"  # This would be set from configuration in a real application
MAX_AGE_MS = 30_000  # 30 seconds

connections: dict[str, ServerConnection] = {}
# Nonce tracking: {nonce: timestamp_ms} - auto-expires after MAX_AGE_MS
used_nonces: dict[str, int] = {}


def cleanup_expired_nonces(max_age_ms: int) -> None:
    """Remove expired nonces from the tracking store."""
    current_time = int(time.time() * 1000)
    expired = [nonce for nonce, timestamp in used_nonces.items() if current_time - timestamp > max_age_ms]
    for nonce in expired:
        del used_nonces[nonce]


def generate_auth_token(secret_key: bytes, nonce: str, timestamp: int | None = None) -> str:
    """Generate HMAC for given nonce and timestamp, base64-encoded for safe header use."""
    if "_" in nonce:
        raise ValueError("Nonce must not contain underscores")
    if timestamp is None:
        timestamp = int(time.time() * 1000)
    msg = f"{nonce}:{timestamp}".encode()
    token = hmac.new(secret_key, msg, hashlib.sha256).hexdigest()
    combined = f"{nonce}__{token}__{timestamp}".encode()
    return base64.urlsafe_b64encode(combined).decode("ascii")


def validate_auth_token(secret_key: bytes, token: str, max_age_ms: int) -> bool:
    """Validate the HMAC token from the Authorization header.

    Prevents replay attacks by tracking used nonces.
    """
    try:
        decoded = base64.urlsafe_b64decode(token).decode("ascii")
        nonce, _, timestamp = decoded.split("__")
    except (ValueError, binascii.Error):
        return False

    # Check timestamp freshness
    if abs(int(time.time() * 1000) - int(timestamp)) > max_age_ms:
        return False

    # Check if nonce has been used (replay attack)
    if nonce in used_nonces:
        return False

    # Regenerate the full token using the same function
    expected_token = generate_auth_token(secret_key, nonce, int(timestamp))

    if not hmac.compare_digest(expected_token, token):
        return False

    # Mark nonce as used and cleanup old nonces
    used_nonces[nonce] = int(timestamp)
    cleanup_expired_nonces(max_age_ms)

    return True


async def Authorization(connection: ServerConnection, request: Request):
    """Check for Authorization header and Server ID in the WebSocket handshake request."""

    auth = request.headers.get("Authorization", "")
    if not auth or not auth.startswith("Bearer "):
        print("Connection Rejected: Missing or invalid Authorization header")
        return Response(
            401, "Unauthorized", Headers([("Content-Type", "text/plain")]), b"Missing or invalid Authorization header"
        )

    token = auth.removeprefix("Bearer ").strip()

    if not validate_auth_token(SECRET_KEY, token, MAX_AGE_MS):
        print("Connection Rejected: Invalid or expired token")
        return Response(401, "Unauthorized", Headers([("Content-Type", "text/plain")]), b"Invalid or expired token")

    return None


async def connection(websocket: ServerConnection):
    """Handle a WebSocket connection for signaling."""

    register_message_tries = 3
    register_message = None
    # Wait for the client to send its server ID via RegisterMessage
    while register_message_tries > 0 and register_message is None:
        try:
            raw_message = await websocket.recv()
        except websockets.exceptions.ConnectionClosed:
            print(f"{websocket.remote_address} disconnected before sending register message")
            return
        try:
            if isinstance(raw_message, bytes):  # Handle binary messages if needed
                raw_message = raw_message.decode("utf-8")
            message_data = json.loads(raw_message)
            register_message = RegisterMessage(**message_data)
        except (json.JSONDecodeError, UnicodeDecodeError, pydantic.ValidationError) as e:
            print(f"{websocket.remote_address} sent invalid register message: {e}")
            reply = ErrorMessage(type="error", message="Invalid register message format", version=1)
            await websocket.send(reply.model_dump_json().encode("utf-8"))
        register_message_tries -= 1

    if register_message is None:
        await websocket.close(1008, "Did not receive register message")
        return
    if register_message_tries == 0 or register_message.type != "register":
        await websocket.close(1008, "Did not receive valid register message")
        return

    server_id = register_message.server_id

    # Replace old connection if reconnecting
    old = connections.get(server_id)
    connections[server_id] = websocket
    if old:
        print(f"{websocket.remote_address} reconnecting, replacing old connection")
        await old.close(1000, "Replaced by reconnect")

    # Send RegisteredMessage back to client
    await websocket.send(RegisteredMessage(type="registered", server_id=server_id, version=1).model_dump_json().encode("utf-8"))

    print(f"{websocket.remote_address} connected with id {server_id}")
    try:
        await websocket.wait_closed()
    finally:
        del connections[server_id]
    print(f"{websocket.remote_address} disconnected")


async def signaling_server(host: str, port: int):
    async with websockets.serve(connection, host, port, process_request=Authorization) as server:
        try:
            print(f"Signaling server started at ws://{host}:{port}")
            while server.is_serving():
                await example_server_usage()  # Place actual message logic here
            await server.serve_forever()
        except (ConnectionClosedOK, ConnectionClosedError):
            print("Signaling server stopped")


async def signaling_client(uri: str, server_id: str, port: int):
    """Connect to the signaling server as a client."""
    nonce = secrets.token_urlsafe(16)
    token = generate_auth_token(SECRET_KEY, nonce)
    headers = {"Authorization": f"Bearer {token}"}
    async with connect(uri, additional_headers=headers) as websocket:
        print(f"Connected to signaling server at {uri}")
        try:
            register_msg = RegisterMessage(
                type="register",
                server_id=server_id,
                mic_stream_count=1,
                cam_stream_count=1,
                accept_output_streams=True,
                roles="ingest-output",
                version=1,
            )
            await websocket.send(register_msg.model_dump_json().encode("utf-8"))
            print(await websocket.recv())  # Wait for RegisteredMessage
            await websocket.wait_closed()
        finally:
            print("Disconnected from signaling server")


async def example_server_usage():
    """Example usage of the signaling server."""
    name = await asyncio.to_thread(input, "Connection name:")
    websockets = connections.get(name)
    if websockets:
        try:
            await websockets.send(f"Hello from server to {name}!")
        except (ConnectionClosedOK, ConnectionClosedError):
            print(f"Connection to {name} is closed, removing from connections list.")
            connections.pop(name, None)
    else:
        print(f"No active connection for {name}.")
    await asyncio.sleep(1)  # Prevent busy loop
