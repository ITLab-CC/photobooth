import React, { useEffect, useState } from "react";

interface AuthenticatedImageProps {
  src: string;
  authToken: string;
  alt: string;
}

const AuthenticatedImage: React.FC<AuthenticatedImageProps> = ({
  src,
  authToken,
  alt,
}) => {
  const [blobUrl, setBlobUrl] = useState<string>("");

  useEffect(() => {
    const fetchImage = async () => {
      try {
        const response = await fetch(src, {
          headers: { Authorization: authToken },
        });
        if (response.ok) {
          const blob = await response.blob();
          const objectUrl = URL.createObjectURL(blob);
          setBlobUrl(objectUrl);
        } else {
          console.error("Error fetching image:", response.statusText);
        }
      } catch (error) {
        console.error("Error fetching image:", error);
      }
    };
    fetchImage();

    return () => {
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
      }
    };
  }, [src, authToken]);

  if (!blobUrl) return <div>Loading...</div>;
  return <img src={blobUrl} alt={alt} style={{ width: "100%" }} />;
};

export default AuthenticatedImage;
