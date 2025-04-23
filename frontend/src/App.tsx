import { BrowserRouter, Routes, Route } from "react-router-dom";
import PhotoBoxPage from "./pages/PhotoBoxPage";
import AdminPage from "./pages/AdminPage";
import DetailPage from "./pages/DetailPage";
import DatenschutzPage from "./pages/DatenschutzPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<PhotoBoxPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/gallery" element={<DetailPage />} />
        <Route path="/datenschutz" element={<DatenschutzPage />} />
      </Routes>
    </BrowserRouter>
  );
}
