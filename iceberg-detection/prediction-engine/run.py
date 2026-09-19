import sys
import os
import argparse
import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Antarctic Iceberg Prediction Engine CLI Runner")
    parser.add_argument("--train", action="store_true", help="Train baseline ML model and exit")
    parser.add_argument("--host", type=str, default=os.getenv("HOST", "0.0.0.0"), help="Host IP")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 8000)), help="Port number")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    if args.train:
        from app.ml.train import train_and_save_model
        model_path = os.getenv("MODEL_PATH", "./models/iceberg_trajectory_model.joblib")
        train_and_save_model(model_path)
        sys.exit(0)

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)
