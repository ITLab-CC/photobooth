import React, { useState } from "react";
import { Box, Typography, Button, Tabs, Tab } from "@mui/material";
import { logout } from "../api";
import { useSnackbar } from "./admin/useSnackbar";
import GalleriesPanel from "./admin/GalleriesPanel";
import BackgroundsPanel from "./admin/BackgroundsPanel";
import FramesPanel from "./admin/FramesPanel";
import SettingsPanel from "./admin/SettingsPanel";
import PrintQueuePanel from "./admin/PrintQueuePanel";

interface AdminDashboardProps {
  token: string;
}

const TABS = ["Galerien", "Hintergründe", "Frames", "Druckwarteschlange", "Einstellungen"] as const;

const AdminDashboard: React.FC<AdminDashboardProps> = ({ token }) => {
  const [activeTab, setActiveTab] = useState(0);
  const { showMessage, SnackbarHost } = useSnackbar();

  return (
    <Box sx={{ p: 3, minHeight: "100vh", backgroundColor: "#f5f5f5" }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
        <Typography variant="h4">Admin Dashboard</Typography>
        <Button
          variant="contained"
          color="error"
          onClick={() => {
            logout(token).then(() => {
              localStorage.removeItem("adminAuthToken");
              window.location.reload();
            });
          }}
        >
          Logout
        </Button>
      </Box>

      <Tabs
        value={activeTab}
        onChange={(_e, value) => setActiveTab(value)}
        sx={{ mb: 3, borderBottom: 1, borderColor: "divider" }}
      >
        {TABS.map((label) => (
          <Tab key={label} label={label} />
        ))}
      </Tabs>

      <Box sx={{ backgroundColor: "#ffffff", borderRadius: 2, p: 3 }}>
        {activeTab === 0 && <GalleriesPanel token={token} showMessage={showMessage} />}
        {activeTab === 1 && <BackgroundsPanel token={token} showMessage={showMessage} />}
        {activeTab === 2 && <FramesPanel token={token} showMessage={showMessage} />}
        {activeTab === 3 && <PrintQueuePanel token={token} showMessage={showMessage} />}
        {activeTab === 4 && <SettingsPanel token={token} showMessage={showMessage} />}
      </Box>

      <SnackbarHost />
    </Box>
  );
};

export default AdminDashboard;
