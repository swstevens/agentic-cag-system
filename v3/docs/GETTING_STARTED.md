# Getting Started with Agentic CAG System (v3)

This guide will help you set up the development environment and run the Agentic CAG System (v3).

## Prerequisites

- **OS**: Linux or macOS recommended (Windows via WSL2)
- **Python**: Version 3.10 or higher
- **Node.js** (Optional): Only if you plan to do heavy frontend customization outside of FastHTML
- **Git**: For version control

## Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/swstevens/agentic-cag-system.git
    cd agentic-cag-system
    ```

2.  **Navigate to v3 Directory**
    The v3 system is self-contained in the `v3` folder.
    ```bash
    cd v3
    ```

3.  **Create a Virtual Environment**
    It's recommended to use a virtual environment to manage dependencies.
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

4.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Environment Configuration**
    Copy the example environment file and configure it.
    ```bash
    cp .env.example .env
    ```
    Open `.env` and add your API keys (e.g., OpenAI, Anthropic, etc.) and configuration preferences.
    ```ini
    # Example .env content
    OPENAI_API_KEY=sk-...
    ANTHROPIC_API_KEY=sk-...
    LLM_MODEL=gpt-4-turbo
    CACHE_SIZE=1000
    ```

## Running the Application

The system consists of two main components: the FastAPI Backend and the FastHTML Frontend. You need to run both.

### 1. Start the Backend
The backend handles API requests, database interactions, and the FSM logic.
```bash
# In terminal 1 (ensure venv is active)
PYTHONPATH=. python3 api.py
```
*The backend runs on `http://localhost:8000`*

### 2. Start the Frontend
The frontend provides the chat interface and deck management UI.
```bash
# In terminal 2 (ensure venv is active)
PYTHONPATH=. python3 frontend/app.py
```
*The frontend runs on `http://localhost:5000`*

## Usage Guide

1.  Open your browser and navigate to `http://localhost:5000`.
2.  **New Deck**: Type a prompt in the chat (e.g., "Build me a Standard Mono-Red Aggro deck").
    - The system will enter the "Draft-Verify-Refine" loop.
    - It might take a minute to generate high-quality results.
3.  **Modify Deck**: Once a deck is loaded, you can ask for changes (e.g., "Swap the Lightning Bolts for Shock").
4.  **Save Deck**: Click the "Save" button to persist your deck to the database.
5.  **View Library**: Click "My Decks" to see your saved decks.

## Troubleshooting

-   **Port Conflicts**: If port 8000 or 5000 is in use, kill the existing process or change the port in `api.py`/`frontend/app.py`.
-   **Database Errors**: If you encounter DB schema errors, try deleting the `.sqlite` file (if it's a dev DB) so it regenerates on startup.
-   **Missing Keys**: Ensure all necessary API keys are set in `.env`.
