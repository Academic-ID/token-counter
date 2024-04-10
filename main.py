from fastapi import FastAPI
from routers import token_router
import os

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    print("Starting up...")
    if not os.getenv('VAULT') and not os.getenv('API-KEY'):
        print("WARNING No keyvault or API-KEY environment variable set")

@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down...")

app.include_router(token_router.router)