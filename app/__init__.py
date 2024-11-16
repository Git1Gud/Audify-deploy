from flask import Flask
import warnings
import torch

def create_app():
    app = Flask(__name__)

    # Configure warnings
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")
    warnings.filterwarnings("ignore", category=UserWarning, module="whisper")
    warnings.filterwarnings("ignore", category=FutureWarning, module="torch")

    print("Torch CUDA availability:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("Using GPU:", torch.cuda.get_device_name(0))

    # Import and register routes
    from .routes import bp as main_routes
    app.register_blueprint(main_routes)

    return app
