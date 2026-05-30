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
- **Python 3.14+** — [download here](https://www.python.org/downloads/)
- **MongoDB** — either run it locally ([install guide](https://www.mongodb.com/docs/manual/installation/)) or use a free cloud instance at [MongoDB Atlas](https://www.mongodb.com/atlas)

### Frontend

shadcn/ui and Tremor are already included as npm dependencies — no extra install needed.

```bash
cd web
npm install
npm run dev
```

The frontend runs on [http://localhost:3000](http://localhost:3000).

### Backend

```bash
cd backend
cp .env.example .env           # Configure your MongoDB connection string
source venv/bin/activate       # Activate the virtual environment
uvicorn app.main:app --reload
```

The API runs on [http://localhost:8000](http://localhost:8000) with docs at [http://localhost:8000/docs](http://localhost:8000/docs).

**Note:** The backend will start even without MongoDB running, but you'll see a warning. Database routes won't work until MongoDB is available.

## License

MIT
