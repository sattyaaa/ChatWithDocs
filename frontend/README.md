# QADoc — React + Vite Frontend

Modern, distraction-free document QA chat interface inspired by the minimalist aesthetics of Claude and ChatGPT.

---

## 🎨 User Interface & Features

* **Minimalist Light Aesthetic:** Refined typography (Inter), subtle borders, soft message bubbles, and smooth micro-animations.
* **Navigation Tabs:**
  * **`💬 Chat`**: Main conversational message stream and floating input dock.
  * **`📁 Documents (N)`**: Ingested files manager displaying searchable vector chunk counts and file deletion controls.
* **Interactive Citations:**
  * Source badges displaying document name, page number, and cross-encoder relevance match score (e.g. `85% match`).
  * Clickable pills that open an excerpt inspection modal with the exact retrieved text.
* **Dynamic Animations:** Active rotating loading animations during file ingestion and while the ReAct agent is querying documents.
* **Auto-Resizing Input Dock:** Floating prompt bar with auto-expanding textarea, drag-and-drop file attachment, and keyboard shortcuts (`Enter` to send, `Shift+Enter` for newline).
* **Multi-Chat Sidebar:** Create, switch, and delete chat sessions with auto-generated topic titles.

---

## 🛠️ Technology Stack

* **Build Tool:** [Vite](https://vitejs.dev/)
* **UI Framework:** [React 19](https://react.dev/)
* **Icons:** [Lucide React](https://lucide.dev/)
* **Markdown Rendering:** [react-markdown](https://github.com/remarkjs/react-markdown) + [remark-gfm](https://github.com/remarkjs/remark-gfm)
* **Styling:** Vanilla CSS with custom tokens, flexbox/grid, and keyframe animations.

---

## 🚀 Development & Build

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Run Local Development Server
```bash
npm run dev
```
Open `http://localhost:5173`. Vite automatically proxies `/api` requests to the FastAPI backend running on `http://localhost:8000`.

### 3. Production Build
```bash
npm run build
```
Generates optimized static assets in `dist/`.
