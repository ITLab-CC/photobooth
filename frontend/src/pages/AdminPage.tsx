import React, { useState } from 'react';
import { Box } from '@mui/material';
import AdminLogin from '../components/AdminLogin';
import AdminDashboard from '../components/AdminDashboard';

const AdminPage: React.FC = () => {
  const [adminToken, setAdminToken] = useState<string | null>(
    localStorage.getItem("adminAuthToken")
  );

  return (
    <Box>
      {!adminToken ? (
        <AdminLogin
          onLogin={(token) => {
            setAdminToken(token);
            localStorage.setItem("adminAuthToken", token);
          }}
        />
      ) : (
        <AdminDashboard token={adminToken} />
      )}
    </Box>
    
  );
};

export default AdminPage;
