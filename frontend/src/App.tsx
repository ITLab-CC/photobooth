// App.tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import AdminPage from "./pages/AdminPage";
import SessionDetailPage from "./pages/SessionDetailPage";
import PhotoboothPage from "./pages/PhotoboothPage";

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<PhotoboothPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/session/:galleryId" element={<SessionDetailPage />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
