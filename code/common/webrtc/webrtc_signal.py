"""This will be the common signaling interface for WebRTC connections using WebSockets."""

import asyncio
import time
import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from websockets.datastructures import Headers
from websockets.asyncio.server import ServerConnection
from websockets.http11 import Request, Response
import hmac
import hashlib

server_id = "placeholder"  # This would be set from configuration in a real application
SECRET_KEY = b"potato"  # This would be set from configuration in a real application
MAX_AGE_MS = 30_000  # 30 seconds

connections: dict = {}


async def generate_hmac(server_id: str, nonce: str) -> str:
    """Generate HMAC for given server ID and nonce."""
    msg = f"{server_id}:{nonce}".encode()
    return hmac.new(SECRET_KEY, msg, hashlib.sha256).hexdigest()


async def Authorization(connection: ServerConnection, request: Request):
    """Check for Authorization header and Server ID in the WebSocket handshake request."""
    id = request.headers.get("X-Server-ID", "")
    if not id:
        print("Connection Rejected: Missing X-Server-ID header")
        return Response(400, "Bad Request", Headers([("Content-Type", "text/plain")]), b"Missing X-Server-ID header")

    connection_nonce = request.headers.get("X-Nonce", "")
    if not connection_nonce:
        print("Connection Rejected: Missing X-Nonce header")
        return Response(400, "Bad Request", Headers([("Content-Type", "text/plain")]), b"Missing X-Nonce header")

    auth = request.headers.get("Authorization", "")
    if not auth or not auth.startswith("Bearer "):
        print("Connection Rejected: Missing or invalid Authorization header")
        return Response(
            401, "Unauthorized", Headers([("Content-Type", "text/plain")]), b"Missing or invalid Authorization header"
        )

    token = auth.removeprefix("Bearer ").strip()
    if abs(int(time.time() * 1000) - int(connection_nonce)) > MAX_AGE_MS:
        return Response(403, "Forbidden", Headers([("Content-Type", "text/plain")]), b"Nonce expired")

    expected_hmac = await generate_hmac(id, connection_nonce)
    if not hmac.compare_digest(expected_hmac, token):
        return Response(403, "Forbidden", Headers([("Content-Type", "text/plain")]), b"Invalid HMAC/token")

    return None


async def connection(websocket):
    """Handle a WebSocket connection for signaling."""
    server_id = websocket.request_headers.get("X-Server-ID")
    if not server_id:
        await websocket.close(1002, "Missing X-Server-ID")
        return

    # Replace old connection if reconnecting
    old = connections.get(server_id)
    connections[server_id] = websocket
    if old:
        print(f"{websocket.remote_address} reconnecting, replacing old connection")
        await old.close(1000, "Replaced by reconnect")

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
                await example_usage()  # Place actual message logic here
            await server.serve_forever()
        except (ConnectionClosedOK, ConnectionClosedError):
            print("Signaling server stopped")


async def example_usage():
    """Example usage of the signaling server."""
    name = await asyncio.to_thread(input, "Your name:")
    websockets = connections.get(name)
    if websockets:
        try:
            await websockets.send(f"Hello from server to {name}!")
        except websockets.exceptions.ConnectionClosed:
            print(f"Connection to {name} is closed, removing from connections list.")
            connections.pop(name, None)
    else:
        print(f"No active connection for {name}.")
    await asyncio.sleep(1)  # Prevent busy loop


if __name__ == "__main__":
    asyncio.run(signaling_server("localhost", 8443))
