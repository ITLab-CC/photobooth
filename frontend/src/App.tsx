import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import PhotoboothPage from "./pages/PhotoboothPage";
import AdminPage from "./pages/AdminPage";

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<PhotoboothPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
