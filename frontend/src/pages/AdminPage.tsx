import React, { useState } from "react";
import { Container, TextField, Button, Typography, Box } from "@mui/material";

const AdminPage: React.FC = () => {
  const [password, setPassword] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const correctPassword = "admin123";

  const handleLogin = () => {
    if (password === correctPassword) {
      setAuthenticated(true);
    } else {
      alert("Falsches Passwort");
    }
  };

  if (!authenticated) {
    return (
      <Container sx={{ mt: 4 }}>
        <Typography variant="h4" align="center" gutterBottom>
          Admin Login
        </Typography>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <TextField
            type="password"
            label="Passwort"
            variant="outlined"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            sx={{ mb: 2, width: "300px" }}
          />
          <Button variant="contained" onClick={handleLogin}>
            Einloggen
          </Button>
        </Box>
      </Container>
    );
  }

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4" align="center" gutterBottom>
        Admin-Bereich
      </Typography>
      <Typography variant="body1" align="center">
        Hier sollten die hochgeladenen Bilder angezeigt werden.
      </Typography>
    </Container>
  );
};

export default AdminPage;
