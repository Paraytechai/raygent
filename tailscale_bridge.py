import asyncio
import sys

async def handle_client(reader, writer):
    try:
        remote_reader, remote_writer = await asyncio.open_connection('127.0.0.1', 8765)
    except Exception:
        writer.close()
        return

    async def pipe(r, w):
        try:
            while True:
                data = await r.read(65536)
                if not data:
                    break
                w.write(data)
                await w.drain()
        except Exception:
            pass
        finally:
            try:
                w.close()
            except Exception:
                pass

    asyncio.create_task(pipe(reader, remote_writer))
    asyncio.create_task(pipe(remote_reader, writer))

async def main():
    server = await asyncio.start_server(handle_client, '0.0.0.0', 8888)
    print("[Tailscale Bridge] Successfully listening on 0.0.0.0:8888 -> 127.0.0.1:8765")
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())
