# Agent Trade Web UI

React-based web UI for visualizing and controlling multi-agent trading experiments.

## Development

### Prerequisites

- Node.js 18+
- npm or yarn
- Python 3.10+ with `agent-trade[web]` installed

### Setup

1. Install frontend dependencies:
```bash
cd web
npm install
```

2. Install backend dependencies:
```bash
# From project root
uv pip install -e ".[web]"
```

### Running in Development Mode

1. Start the FastAPI backend (from project root):
```bash
agent-trade-web
```
This starts the API server on http://localhost:8000

2. In a separate terminal, start the Vite dev server:
```bash
cd web
npm run dev
```
This starts the frontend on http://localhost:5173 with hot reload.

The Vite dev server proxies `/api` requests to the FastAPI backend.

### Building for Production

```bash
cd web
npm run build
```

The production build is created in `web/dist/`. The FastAPI server automatically serves these static files when running `agent-trade-web`.

## Architecture

- **Frontend**: Vite + React + TypeScript + Tailwind CSS
- **State Management**: TanStack Query for server state
- **Charts**: Recharts for data visualization
- **Backend**: FastAPI serving both API and static files
- **API**: RESTful endpoints at `/api/v1/*`

## Phase 1 Implementation

This is Phase 1 of the web UI implementation, which includes:

### Backend
- FastAPI application with CORS support
- Experiment list and detail endpoints
- Game state endpoint
- Response schemas with Decimal to float conversion

### Frontend
- React application with TypeScript
- Dashboard page with experiment cards
- Experiment detail page with agent overview
- Routing with React Router
- TanStack Query for data fetching
- Custom brand color palette (green gradient)

## Next Phases

- **Phase 2**: Leaderboard + Performance Charts
- **Phase 3**: Agent Detail View (portfolio breakdown, strategy, transactions)
- **Phase 4**: Run Controls + Real-time Updates (SSE)
- **Phase 5**: Analysis & Visualization (tax metrics, holding periods)
- **Phase 6**: Polish & Deployment (forms, responsive, dark mode)
