import React, { useState } from "react";
import { Button, TextField, Typography, Paper } from "@mui/material";
import { login } from "../api"; 

interface AdminLoginProps {
  onLogin: (token: string) => void;
}

const AdminLogin: React.FC<AdminLoginProps> = ({ onLogin }) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async () => {
    try {
      const response = await login(username, password);
      onLogin(response.token);
      localStorage.setItem("adminAuthToken", response.token);
    } catch (err) {
      console.error("Login fehlgeschlagen:", err);
      alert("Login fehlgeschlagen");
    }
  };

  return (
    <Paper sx={{ p: 3, maxWidth: 400, margin: "auto", mt: 4 }}>
      <Typography variant="h5" sx={{ mb: 2, textAlign: "center" }}>
        Admin Login
      </Typography>
      <TextField
        label="Benutzername"
        fullWidth
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        sx={{ mb: 2 }}
      />
      <TextField
        label="Passwort"
        type="password"
        fullWidth
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        sx={{ mb: 2 }}
      />
      <Button variant="contained" fullWidth onClick={handleSubmit}>
        Login
      </Button>
    </Paper>
  );
};

export default AdminLogin;
