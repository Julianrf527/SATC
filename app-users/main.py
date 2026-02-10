from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, notification, role, user, email

app = FastAPI()

# CORS: cambia esto en producción
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(user.router, prefix="/user", tags=["Users"])
app.include_router(notification.router, prefix="/notification", tags=["Notifications"])
app.include_router(role.router, prefix="/role", tags=["Roles"])
app.include_router(email.router, prefix="/email", tags=["Email"])


# correr directamente: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
