# Img file server
.env
```.env
MONGODB_ROOT_USER=admin
MONGODB_ROOT_PASSWORD=admin
```

poetry install

poetry env activate
source /home/user/.cache/pypoetry/virtualenvs/img-server-XKSOv4nP-py3.10/bin/activate
docker compose up -d
cd src/img_server
python main.py