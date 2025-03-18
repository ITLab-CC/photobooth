import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Box, Typography, Grid, Card, CardMedia } from '@mui/material';
import { getGalleryImagesByPin } from '../api';

export default function GalleryPage() {
  const { galleryId, pin } = useParams<{ galleryId: string; pin: string }>();
  const [images, setImages] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!galleryId || !pin) return;
    getGalleryImagesByPin(galleryId, pin)
      .then((res) => {
        const newImages = res.images.map((imgObj) => {
          return `/api/v1/gallery/${galleryId}/image/${imgObj.image_id}/pin/${pin}`;
        });
        setImages(newImages);
      })
      .catch((err) => {
        console.error(err);
        setError('Fehler beim Laden der Galerie-Bilder');
      });
  }, [galleryId, pin]);

  if (error) {
    return (
      <Box sx={{ p: 4 }}>
        <Typography color="error">{error}</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 4 }}>
      <Typography variant="h4" gutterBottom>
        Galerie {galleryId}
      </Typography>
      <Grid container spacing={2}>
        {images.map((imgUrl, index) => (
          <Grid item xs={12} sm={6} md={4} key={index}>
            <Card>
              <CardMedia
                component="img"
                image={imgUrl}
                alt={`Bild ${index + 1}`}
              />
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
