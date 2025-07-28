from source.web_app.app import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8080)
    # uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=True)