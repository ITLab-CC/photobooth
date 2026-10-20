import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider, CssBaseline } from "@mui/material";
import PhotoBoxPage from "./pages/PhotoBoxPage";
import AdminPage from "./pages/AdminPage";
import { appTheme } from "./theme";

export default function App() {
  return (
    <ThemeProvider theme={appTheme}>
      <CssBaseline />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<PhotoBoxPage />} />
          <Route path="/admin" element={<AdminPage />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}
