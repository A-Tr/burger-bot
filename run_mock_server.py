"""Script to run the mock burger joint API server."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("mock_server.server:app", host="0.0.0.0", port=8000, reload=True)

