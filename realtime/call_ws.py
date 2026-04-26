import asyncio
import websockets
import json

rooms = {}


async def safe_send(ws, data):
    try:
        await ws.send(json.dumps(data))
    except:
        pass


async def handler(ws):
    room_id = None

    try:
        async for message in ws:
            print("Received:", message)

            try:
                data = json.loads(message)
            except:
                continue

            # =========================
            # JOIN ROOM
            # =========================
            if data.get("type") == "join":

                room_id = data["room"]

                if room_id not in rooms:
                    rooms[room_id] = []

                if len(rooms[room_id]) >= 2:
                    await safe_send(ws, {"type": "full"})
                    continue

                rooms[room_id].append(ws)

                if len(rooms[room_id]) == 1:
                    await safe_send(ws, {"type": "waiting"})

                elif len(rooms[room_id]) == 2:
                    for client in rooms[room_id]:
                        await safe_send(client, {"type": "ready"})

            # =========================
            # SIGNALING (WEBRTC)
            # =========================
            elif data.get("type") in ["offer", "answer", "ice", "call", "accept"]:
                if room_id in rooms:
                    for client in rooms[room_id]:
                        if client != ws:
                            await safe_send(client, data)

            # =========================
            # 🔥 LIVE TRANSLATION (FIXED)
            # =========================
            elif data.get("type") == "translated_audio":

                # 🔥 IMPORTANT: just forward the audio URL
                if "audio" not in data:
                    continue

                if room_id in rooms:
                    for client in rooms[room_id]:
                        if client != ws:
                            await safe_send(client, {
                                "type": "translated_audio",
                                "audio": data["audio"]
                            })

    except Exception as e:
        print("Client disconnected:", e)

    finally:
        if room_id in rooms and ws in rooms[room_id]:
            rooms[room_id].remove(ws)

            for client in rooms[room_id]:
                await safe_send(client, {"type": "waiting"})

            if len(rooms[room_id]) == 0:
                del rooms[room_id]