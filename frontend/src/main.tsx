import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css'; 

console.log("Starte App");

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error("Kein Element mit id 'root' gefunden.");
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
