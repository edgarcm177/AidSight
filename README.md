# AidSight

Portfolio stress-testing terminal for humanitarian funding. A Decision Sandbox to identify funding gaps, run stress tests, rebalance under constraints, benchmark with comparable projects, and generate Investment Committee memos.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ and Python 3.11+ (for local dev without Docker)

### Run with Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000
- Web: http://localhost:3000
- Docs: http://localhost:8000/docs

### Local Development

**Backend**
```bash
cd apps/api
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend**
```bash
cd apps/web
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `.env.local` or `.env` for the web app.

## Project Structure

```
AidSight/
├── apps/
│   ├── api/          # FastAPI backend
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── services/
│   │   │   ├── data_provider.py
│   │   │   ├── scenario_engine.py
│   │   │   ├── vector_service.py
│   │   │   └── memo_service.py
│   │   └── mock_data/
│   │       ├── regions.json
│   │       └── projects.json
│   └── web/          # Next.js frontend
│       ├── app/      # App Router pages
│       ├── components/
│       └── lib/
├── geo/              # GeoJSON (replace with real countries.geojson)
├── pipelines/        # Data prep placeholders
├── docs/
│   ├── ARCHITECTURE.md
│   └── API_CONTRACT.md
├── docker-compose.yml
└── .env.example
```

## Swapping Mock Data for Production

1. **Data**: Implement a new `DataProvider` (e.g. `DatabricksDataProvider`) that reads from your warehouse. Ensure output conforms to `RegionMetric` and `Project` schemas. Wire it in `main.py` instead of `MockDataProvider`.

2. **Vector DB**: Set `ACTIAN_ENDPOINT` and `ACTIAN_API_KEY` in `.env`. Implement `RealActianVectorClient` in `vector_service.py` with real HTTP calls to Actian VectorAI `upsert` and `query` endpoints.

3. **Sphinx AI**: Set `SPHINX_ENDPOINT` and `SPHINX_API_KEY`. Implement `RealSphinxClient.generate_memo()` in `memo_service.py` to POST context to Sphinx and parse structured sections.

4. **GeoJSON**: Replace `geo/countries.geojson` and `apps/web/public/geo/countries.geojson` with a real countries file. Ensure each feature has `region_id` (or `id`) matching your region IDs.
