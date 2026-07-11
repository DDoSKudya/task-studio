from studio_common.app import create_service_app, service_port
from studio_common.runtime import bind_host

app = create_service_app("catalog")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=bind_host(), port=service_port(8002), factory=False)
