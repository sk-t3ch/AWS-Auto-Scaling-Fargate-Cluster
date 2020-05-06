from aiohttp import web
import aiohttp_cors
import json

async def healthcheck(_):
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return web.Response(text=json.dumps("Healthy"), headers=headers, status=200)
 
async def helloworld(_):
    return web.Response(text="<h1>HELLO WORLD</h1>", content_type='text/html', status=200)


app = web.Application()
cors = aiohttp_cors.setup(app)
app.router.add_get("/healthcheck", healthcheck)
app.router.add_get("/", helloworld)

cors = aiohttp_cors.setup(app, defaults={
    "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
})

# Configure CORS on all routes.
for route in list(app.router.routes()):
    cors.add(route)

if __name__ == "__main__":
    print("Starting service")
    web.run_app(app, host="0.0.0.0", port=(5000))
    