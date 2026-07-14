from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.vacancies.routers import router as vacancies_router

app = FastAPI()
app.include_router(vacancies_router)

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
