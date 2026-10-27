"""Public, isolated demo entrypoint for Streamlit Community Cloud."""
import os

os.environ["PUBLIC_DEMO_MODE"] = "1"

from app import main

main()
