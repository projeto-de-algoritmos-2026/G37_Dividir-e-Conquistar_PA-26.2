import { createRoot } from "react-dom/client";
import App from "./App.jsx";

// Leaflet via npm (nao mais pelo CDN)
import "leaflet/dist/leaflet.css";
import "./index.css";

// Sem StrictMode de proposito: o StrictMode monta/desmonta/monta em dev e o
// Leaflet imperativo reclama ("Map container is already initialized").
createRoot(document.getElementById("root")).render(<App />);
