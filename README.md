# Catalog Integrity Checker

This Streamlit application helps ensure the integrity of your product catalog by cross-referencing inventory and lifecycle statuses between Shopify and Dynamics 365 exports. It generates a bulk-import fix file for Shopify, preventing issues like phantom inventory and overselling.

## Features
- Upload Shopify and Dynamics 365 CSV exports.
- Configure inventory buffer thresholds and discontinued item keywords.
- Identifies items that need to be 'Drafted' (due to low stock) or 'Archived' (if discontinued).
- Generates a downloadable CSV file ready for Shopify import to apply fixes.
- Provides an executive summary of anomalies detected.

## How to Run Locally

1.  **Clone the repository**:
    ```bash
    git clone <your-repository-url>
    cd <your-repository-name>
    ```

2.  **Create a virtual environment (recommended)**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Streamlit application**:
    ```bash
    streamlit run app.py
    ```

    Your browser will open to the Streamlit app.

## How to Deploy to Streamlit Community Cloud

1.  **Push your code to GitHub**: Ensure all files (`app.py`, `requirements.txt`, `README.md`, `LICENSE`, `.gitignore`) are pushed to a public GitHub repository.
2.  **Go to Streamlit Community Cloud**: Log in at [share.streamlit.io](https://share.streamlit.io/).
3.  **Deploy a new app**: Select 'New app' and connect your GitHub repository. Choose `app.py` as your main file.
4.  **Launch**: Click deploy, and your application will be live!
