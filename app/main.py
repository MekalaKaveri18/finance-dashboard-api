from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import Base, engine
from app.routers import auth, users, records, dashboard

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Finance Dashboard API",
    description="Role-based finance data management backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(records.router, prefix="/api/records", tags=["Financial Records"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Finance Dashboard API is running"}
