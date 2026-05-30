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

- Node.js 20+
- Python 3.14+
- MongoDB (local or Atlas)

### Frontend

```bash
cd web
npm install
npm run dev
```

The frontend runs on [http://localhost:3000](http://localhost:3000).

### Backend

```bash
cd backend
cp .env.example .env      # Configure MongoDB connection
source venv/bin/activate
uvicorn app.main:app --reload
```

The API runs on [http://localhost:8000](http://localhost:8000) with docs at [http://localhost:8000/docs](http://localhost:8000/docs).

## License

MIT
