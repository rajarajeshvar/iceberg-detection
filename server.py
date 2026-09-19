import os
import sys
import importlib.util

base_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.join(base_dir, "Iceberg detection-segmentation")

if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Load server module directly from Iceberg detection-segmentation
server_path = os.path.join(project_dir, "server.py")
spec = importlib.util.spec_from_file_location("iceberg_server", server_path)
iceberg_server = importlib.util.module_from_spec(spec)
sys.modules["iceberg_server"] = iceberg_server
spec.loader.exec_module(iceberg_server)

app = iceberg_server.app

if __name__ == "__main__":
    import uvicorn
    print("Starting Sentinel-1 SAR Iceberg Segmentation Server on http://127.0.0.1:8000 ...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
