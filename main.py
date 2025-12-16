from fastapi import FastAPI
from routers import pins, boards

app = FastAPI(title="Pinterest Scheduler")

# Register routers
app.include_router(pins.router)
app.include_router(boards.router)
