from fastapi import FastAPI

app = FastAPI(title="SmartDocs AI")

@app.get("/health")
def health():
    return {"status": "healthy"}