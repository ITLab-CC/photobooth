import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { login } from '../api';

interface AutoLoginProps {
  onToken: (token: string) => void;
}

export default function AutoLogin({ onToken }: AutoLoginProps) {
  const navigate = useNavigate();

  useEffect(() => {
    const storedToken = localStorage.getItem('photoBoothToken');
    if (storedToken) {
      onToken(storedToken);
      navigate('/', { replace: true });
      return;
    }

    const params = new URLSearchParams(window.location.search);
    const user = params.get('user');
    const password = params.get('password');

    if (user && password) {
      login(user, password)
        .then((authResponse) => {
          onToken(authResponse.token);
          localStorage.setItem('photoBoothToken', authResponse.token);
          navigate('/', { replace: true });
        })
        .catch((err) => {
          console.error('AutoLogin fehlgeschlagen:', err);
        });
    }
  }, [onToken, navigate]);

  return null;
}
