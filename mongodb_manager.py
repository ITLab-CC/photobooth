import io
import time
from typing import Optional, Union
from bson import Binary
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from PIL import Image
from dataclasses import asdict, dataclass

from img import IMG

class MongoDBManager:
    """
    A simple MongoDB manager to handle storing and loading IMG objects.
    """

    @dataclass
    class DBCollection:
        name: str
        type: type
        collection: Collection

    def __init__(self,
                 mongo_uri: str,
                 user: str,
                 password: str,
                 db_name: str,
                 background_collection_name: str,
                 images_collection_name: str
                 ) -> None:
        new_uri = f"mongodb://{user}:{password}@{mongo_uri}"
        self.client: MongoClient = MongoClient(new_uri)
        self.db: Database = self.client[db_name]
        # We store a dictionary mapping logical names to their settings
        self.collections: dict[str, MongoDBManager.DBCollection] = {
            "background": MongoDBManager.DBCollection(
                name=background_collection_name,
                type=IMG,
                collection=self.db[background_collection_name]
            ),
            "images": MongoDBManager.DBCollection(
                name=images_collection_name,
                type=IMG,
                collection=self.db[images_collection_name]
            )
        }

        self._setup_collections()

    def _setup_collections(self) -> None:
        """
        Create the required collections in the database with proper validators
        and ensure a unique index on the _id field.
        """
        existing_collections = self.db.list_collection_names()
        for coll_name, coll_info in self.collections.items():
            if coll_name not in existing_collections:
                coll_info_type = coll_info.type
                if not hasattr(coll_info_type, "_mongodb_collection"):
                    raise ValueError(f"Type '{coll_info_type}' does not have a _mongodb_collection method.")
                schema = coll_info_type._mongodb_collection()
                # Create the collection with the validator options.
                self.db.create_collection(
                    name=coll_name,
                    validator=schema["validator"],
                    validationLevel=schema["validationLevel"],
                    validationAction=schema["validationAction"]
                )
                # Update the collection handle after creation.
                coll_info.collection = self.db[coll_name]
            # Create a unique index on _id.
            # coll_info["collection"].create_index("_id", unique=True)

    def _get_collection(self, collection_name: str, type_: type) -> Collection:
        if collection_name not in self.collections:
            raise ValueError(f"Collection '{collection_name}' not found in DB.")
        
        if self.collections[collection_name].type != type_:
            raise ValueError(f"Collection '{collection_name}' accepts only "
                             f"{self.collections[collection_name].type} objects.")
        
        return self.collections[collection_name].collection

    def store_img(self, img_obj: IMG, collection_name: str) -> None:
        """
        Store an IMG object in MongoDB by converting PIL.Image to binary.
        """
        collection = self._get_collection(collection_name, IMG)
        doc = asdict(img_obj)
        
        # Convert the PIL image to raw bytes.
        with io.BytesIO() as output:
            doc["img"].save(output, format="PNG")  # or another desired format
            img_bytes = output.getvalue()
        
        # Replace the 'img' field with a BSON Binary.
        doc["img"] = Binary(img_bytes)

        # Insert the document.
        collection.insert_one(doc)
        print(f"Stored: {img_obj}")

    def load_img(self, img_id: str, collection_name: str) -> IMG:
        """
        Retrieve an IMG object by its id from MongoDB, converting
        raw bytes back to a PIL.Image.
        """
        collection = self._get_collection(collection_name, IMG)
        data = collection.find_one({"_id": img_id})
        if data is not None:
            # Convert the binary data back into a PIL image and copy it so the stream can close.
            img_bytes = data["img"]
            with io.BytesIO(img_bytes) as stream:
                image = Image.open(stream).copy()  # .copy() loads the image data into memory.
            data["img"] = image
            return IMG(**data)
        raise ValueError(f"IMG object with id '{img_id}' not found in DB.")

    def get_all_imgs(self, collection_name: str) -> list[IMG]:
        """
        Retrieve all IMG objects from a collection in MongoDB.
        """
        collection = self._get_collection(collection_name, IMG)
        all_images = []
        for data in collection.find():
            # Convert the binary data back into a PIL image and copy it so the stream can close.
            img_bytes = data["img"]
            with io.BytesIO(img_bytes) as stream:
                image = Image.open(stream).copy()
            data["img"] = image
            all_images.append(IMG(**data))
        return all_images

    
    def update_img(self, img_obj: IMG, collection_name: str) -> None:
        """
        Update an existing IMG object in MongoDB by converting the PIL.Image
        to binary and replacing the document with the updated values.
        """
        collection = self._get_collection(collection_name, IMG)
        
        # Convert the IMG object to a dictionary.
        doc = asdict(img_obj)
        
        # Convert the PIL image to raw bytes.
        with io.BytesIO() as output:
            doc["img"].save(output, format="PNG")  # or another desired format
            img_bytes = output.getvalue()
        
        # Replace the 'img' field with a BSON Binary.
        doc["img"] = Binary(img_bytes)
        
        # Update the document in MongoDB by matching the _id field.
        result = collection.update_one({"_id": img_obj.id}, {"$set": doc})
        
        if result.matched_count == 0:
            raise ValueError(f"IMG object with id '{img_obj.id}' not found in DB.")
        
        print(f"Updated: {img_obj}")


    def remove_img(self, img_id: str, collection_name: str) -> None:
        """
        Remove an IMG object from MongoDB by its id.
        """
        collection = self._get_collection(collection_name, IMG)
        collection.delete_one({"_id": img_id})
        print(f"Removed IMG object with id: {img_id}")

    def get_all_imgs_of_gallery(self, gallery_id: str, collection_name: str) -> list[IMG]:
        """
        Retrieve all IMG objects from a gallery in MongoDB.
        """
        collection = self._get_collection(collection_name, IMG)
        all_images = []
        for data in collection.find({"gallery": gallery_id}):
            # Convert the binary data back into a PIL image and copy it so the stream can close.
            img_bytes = data["img"]
            with io.BytesIO(img_bytes) as stream:
                image = Image.open(stream).copy()
            data["img"] = image
            all_images.append(IMG(**data))
        return all_images

if __name__ == "__main__":
    # Initialize the MongoDB manager.
    mongo_manager = MongoDBManager(
        mongo_uri="localhost:27017",
        user="root",
        password="example",
        db_name="photobooth",
        images_collection_name="images",
        background_collection_name="background"
    )

    # Create an IMG object.
    input_img = Image.open("./image.png")
    img1 = IMG(img=input_img, name="Sample Image", description="An example image.")
    
    # Store the IMG object.
    mongo_manager.store_img(img1, collection_name="background")

    # Load it back using its ID.
    loaded_img = mongo_manager.load_img(img1.id, collection_name="background")
    print(f"Loaded from DB: {loaded_img}")

    # Save the loaded image to disk.
    loaded_img.img.save("./loaded_image.png")

    # Update the description and store it back.
    loaded_img.description = "An updated description."
    mongo_manager.update_img(loaded_img, collection_name="background")

    # List all images in the collection.
    all_images = mongo_manager.get_all_imgs(collection_name="background")
    for img in all_images:
        print(img)

    time.sleep(10)
    # Remove the IMG object.
    mongo_manager.remove_img(loaded_img.id, collection_name="background")


    # Add a new image to with a gallery ID.
    img2 = IMG(img=input_img, name="Another Image", description="Another example image.", gallery="gallery-1")
    mongo_manager.store_img(img2, collection_name="images")

    # Retrieve all images in a gallery.
    all_gallery_images = mongo_manager.get_all_imgs_of_gallery("gallery-1", collection_name="images")

    for img in all_gallery_images:
        print(img)
