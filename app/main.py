from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.scheduler.tasks import setup_scheduler
from app.vacancies.routers import router as vacancies_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = setup_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)
app.include_router(vacancies_router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", reload=True)
