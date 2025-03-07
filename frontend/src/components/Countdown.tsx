import React, { useEffect, useState } from "react";
import { Typography } from "@mui/material";

interface CountdownProps {
  seconds: number;
  onComplete: () => void;
}

const Countdown: React.FC<CountdownProps> = ({ seconds, onComplete }) => {
  const [count, setCount] = useState(seconds);

  useEffect(() => {
    if (count <= 0) {
      onComplete();
      return;
    }
    const timer = setTimeout(() => setCount(count - 1), 1000);
    return () => clearTimeout(timer);
  }, [count, onComplete]);

  return (
    <Typography variant="h3" align="center" color="white">
      {count}
    </Typography>
  );
};

export default Countdown;
