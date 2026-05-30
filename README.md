# MPC Hacks 2026

A hackathon project built with Next.js, React, TypeScript, shadcn/ui, Tremor, MongoDB, and Python.

## Tech Stack

**Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS v4, shadcn/ui, Tremor
**Backend:** Python 3.14, FastAPI, MongoDB (Motor)
**Database:** MongoDB

## Project Structure

```
web/          # Next.js frontend app
backend/      # Python FastAPI backend
```

## Getting Started

### Prerequisites

These must be installed on your machine before the project will run:

- **Node.js 20+** — [download here](https://nodejs.org/)
- **npm** (comes with Node.js) or **pnpm** if you prefer
- **Python 3.14+** — [download here](https://www.python.org/downloads/)
- **MongoDB** — either run it locally ([install guide](https://www.mongodb.com/docs/manual/installation/)) or use a free cloud instance at [MongoDB Atlas](https://www.mongodb.com/atlas)

> If `npm install` fails in `web/`, make sure your Node version is 20 or newer. You can check with:
>
> ```bash
> node -v
> npm -v
> ```

### Frontend setup

1. Open a terminal and navigate to the frontend folder:

    ```bash
    cd web
    ```

2. Install frontend dependencies:

    ```bash
    npm install
    ```

    If you see dependency resolution errors, try:

    ```bash
    npm install --legacy-peer-deps
    ```

3. Start the development server:

    ```bash
    npm run dev
    ```

4. Open the app in your browser at:

    ```text
    http://localhost:3000
    ```

### Backend setup

1. Open a terminal and navigate to the backend folder:

    ```bash
    cd backend
    ```

2. Create a Python virtual environment (if one does not already exist):

    ```bash
    python3 -m venv venv
    ```

3. Activate the virtual environment:

    ```bash
    source venv/bin/activate
    ```

4. Install backend Python dependencies:

    ```bash
    pip install -r requirements.txt
    ```

5. Copy the example environment file and configure your MongoDB connection:

    ```bash
    cp .env.example .env
    ```

6. Start the FastAPI server:

    ```bash
    uvicorn app.main:app --reload
    ```

7. Verify the backend is running:

    ```text
    http://localhost:8000
    ```

    API docs are available at:

    ```text
    http://localhost:8000/docs
    ```

### Recommended order

1. Start MongoDB or configure MongoDB Atlas.
2. Run the backend:

    ```bash
    cd backend
    source venv/bin/activate
    uvicorn app.main:app --reload
    ```

3. Run the frontend:

    ```bash
    cd web
    npm install
    npm run dev
    ```

## License

MIT
