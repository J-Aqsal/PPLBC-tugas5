from flask import Flask, render_template, request
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
import psycopg
import os
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)


DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

def get_connection():
    return psycopg.connect(**DB_CONFIG) # tambah TRY

def db_execute(query, params=None, many=False):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if many:
                cur.executemany(query, params)
            else:
                cur.execute(query, params)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# =========================
# Azure Blob Storage
# =========================
AZURE_STORAGE_ACCOUNT = os.getenv("AZURE_STORAGE_ACCOUNT")
AZURE_STORAGE_KEY = os.getenv("AZURE_STORAGE_KEY")
AZURE_CONTAINER = os.getenv("AZURE_CONTAINER")

connection_string = (
    f"DefaultEndpointsProtocol=https;"
    f"AccountName={AZURE_STORAGE_ACCOUNT};"
    f"AccountKey={AZURE_STORAGE_KEY};"
    f"EndpointSuffix=core.windows.net"
)

blob_service_client = BlobServiceClient.from_connection_string(
    connection_string
)

container_client = blob_service_client.get_container_client(
    AZURE_CONTAINER
)

# =========================
# Routes
# =========================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/submit", methods=["POST"])
def submit():

    nama = request.form["nama"]
    email = request.form["email"]
    gambar = request.files["gambar"]

    filename = secure_filename(gambar.filename)

    # =========================
    # Upload to Azure Blob
    # =========================
    blob_client = container_client.get_blob_client(filename)

    blob_client.upload_blob(
        gambar,
        overwrite=True
    )

    image_url = (
        f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/"
        f"{AZURE_CONTAINER}/{filename}"
    )

    # =========================
    # Insert into PostgreSQL
    # =========================

    db_execute(
        """
        INSERT INTO pelamar (nama, email, image_url)
        VALUES (%s, %s, %s)
        """,
        (nama, email, image_url)
    )
    return render_template(
        "index.html",
        message="Data berhasil disimpan!"
    )


if __name__ == "__main__":
    app.run(debug=True)