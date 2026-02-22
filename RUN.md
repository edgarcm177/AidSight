# How to Run AidSight

Run all commands from the **project root**: `c:\Users\wgq19\Downloads\AidSight`

---

## 1. Backend (required first)

**Install Python dependencies (do this once):**
```powershell
cd c:\Users\wgq19\Downloads\AidSight
pip install -r backend\requirements.txt
```

**Start the API server:**
```powershell
cd c:\Users\wgq19\Downloads\AidSight
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

- Leave this terminal open.
- Backend URL: **http://localhost:8000**
- API docs: **http://localhost:8000/docs**

If you see `ModuleNotFoundError: No module named 'sklearn'` (or similar), run `pip install -r backend\requirements.txt` again from the project root.

---

## 2. Frontend

**Install Node dependencies (do this once):**
```powershell
cd c:\Users\wgq19\Downloads\AidSight\frontend
npm install
```

**Start the dev server:**
```powershell
cd c:\Users\wgq19\Downloads\AidSight\frontend
npm run dev
```

- Leave this terminal open.
- Open the URL shown in the terminal (e.g. **http://localhost:5173** or **http://localhost:5174**).
- Use that exact URL in your browser; if 5173 is in use, Vite will use 5174.

---

## Checklist

- [ ] Backend: `pip install -r backend\requirements.txt` (once)
- [ ] Backend: `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000` (from project root)
- [ ] Frontend: `npm install` in `frontend` (once)
- [ ] Frontend: `npm run dev` in `frontend`, then open the URL it prints

If "page cannot be opened":
- Backend: ensure the first terminal is still running and shows no errors; open http://localhost:8000/docs to test.
- Frontend: ensure the second terminal is still running; use the **exact** URL it prints (e.g. http://localhost:5174 if it says 5174).
