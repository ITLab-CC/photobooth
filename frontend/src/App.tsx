import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider, CssBaseline } from "@mui/material";
import PhotoBoxPage from "./pages/PhotoBoxPage";
import AdminPage from "./pages/AdminPage";
import DetailPage from "./pages/DetailPage";
import { appTheme } from "./theme";

export default function App() {
  return (
    <ThemeProvider theme={appTheme}>
      <CssBaseline />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<PhotoBoxPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/gallery" element={<DetailPage />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}
