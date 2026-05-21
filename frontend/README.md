# JobPortal AI - Frontend

This is the frontend presentation layer for the JobPortal AI platform. It is a single-page application (SPA) built using React and Vite, focusing on performance, modularity, and a premium visual aesthetic.

## 🛠️ Technology Stack
- **Framework:** React 18 + Vite (for lightning-fast HMR and building)
- **Routing:** React Router DOM (v6)
- **Styling:** Vanilla CSS with custom CSS variables, gradients, and a sleek dark mode glassmorphism UI.
- **HTTP Client:** Axios (configured with intercepts for authentication tokens)
- **Icons:** Lucide React (clean, consistent SVG iconography)
- **Real-time Data:** Server-Sent Events (SSE) using the native `EventSource` API to display live scraper console logs in the Admin Dashboard.

## 📂 Project Architecture
```
frontend/
├── index.html         # Main HTML entry point
├── package.json       # Project dependencies
├── src/
│   ├── App.jsx        # Main application router
│   ├── index.css      # Global CSS variables and glassmorphism themes
│   ├── main.jsx       # React DOM rendering
│   ├── api/
│   │   └── client.js  # Axios instance configuration
│   ├── components/    # Reusable UI elements (Navbar, JobCard, etc.)
│   └── pages/         # Route-level components
│       ├── Home.jsx           # Job search and listing interface
│       ├── ResumeAI.jsx       # PDF upload and Gemini AI feedback UI
│       ├── AdminLogin.jsx     # Secure JWT login portal
│       └── AdminDashboard.jsx # Analytics and scraper controls
```

## 🎨 Design Philosophy
The UI was built with a "premium first" mindset. It avoids heavy CSS frameworks like Tailwind or Bootstrap in favor of highly customized CSS logic. Key design elements include:
- Deep dark backgrounds with subtle radial gradients (purple/cyan) to draw user focus.
- Blur backdrops (glassmorphism) for cards and modals.
- Interactive micro-animations (hover states, spinning loading indicators).

## 🚀 Getting Started

1. Ensure Node.js is installed.
2. Navigate to the `frontend` directory: `cd frontend`
3. Install dependencies: `npm install`
4. Run the development server: `npm run dev`

By default, the application runs on `http://localhost:5173`. It assumes the backend API is running on `http://localhost:8000`.
