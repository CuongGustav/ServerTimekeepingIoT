from flask import Flask, request, jsonify, send_file, Response
import psycopg2
import os
import uuid
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Thư mục chứa ảnh
UPLOAD_FOLDER = 'statics'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Kết nối đến PostgreSQL
conn = psycopg2.connect(
    dbname="dbiot06",
    user="dbiot06_user",
    password="nMnOWsqIF12dIU0L9sYhMjQakH6skpMN",
    host="dpg-ct68db5umphs7394idtg-a.singapore-postgres.render.com",
    port="5432"
)

# Tạo bảng nếu chưa tồn tại
def create_all_tables():
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS text_data (
                id SERIAL PRIMARY KEY,
                status TEXT NOT NULL,
                userId TEXT NOT NULL
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS image_data (
                id SERIAL PRIMARY KEY,
                image_path TEXT NOT NULL
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS status (
                id SERIAL PRIMARY KEY,
                image_status BOOLEAN DEFAULT TRUE,
                status_status BOOLEAN DEFAULT TRUE,
                userId_status BOOLEAN DEFAULT TRUE
            );
        """)
        # Khởi tạo trạng thái nếu chưa tồn tại
        cur.execute("INSERT INTO status (id) VALUES (1) ON CONFLICT (id) DO NOTHING;")
        conn.commit()

create_all_tables()

# Xóa toàn bộ dữ liệu hiện tại
def clear_data():
    with conn.cursor() as cur:
        # Xóa dữ liệu trong database
        cur.execute("DELETE FROM text_data;")
        cur.execute("DELETE FROM image_data;")
        # Xóa ảnh trong thư mục static
        for file in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        # Cập nhật trạng thái
        cur.execute("""
            UPDATE status 
            SET image_status = FALSE, status_status = FALSE, userId_status = FALSE
            WHERE id = 1;
        """)
        conn.commit()

# Endpoint send_data
@app.route('/send_data', methods=['POST'])
def send_data():
    # Kiểm tra dữ liệu đầu vào
    status = request.form.get('status')
    userId = request.form.get('userId')
    image = request.files.get('image')

    if not status or not userId or not image:
        return jsonify({"error": "Missing data"}), 400

    # Xóa dữ liệu hiện tại nếu có dữ liệu mới
    clear_data()

    # Lưu ảnh vào thư mục static
    image_name = f"{uuid.uuid4().hex}_{image.filename}"
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name)
    image.save(image_path)

    # Lưu dữ liệu mới vào database
    with conn.cursor() as cur:
        cur.execute("INSERT INTO text_data (status, userId) VALUES (%s, %s);", (status, userId))
        cur.execute("INSERT INTO image_data (image_path) VALUES (%s);", (image_path,))
        cur.execute("""
            UPDATE status 
            SET image_status = TRUE, status_status = TRUE, userId_status = TRUE
            WHERE id = 1;
        """)
        conn.commit()

    return jsonify({"message": "Data saved successfully"}), 200

# # Endpoint get_data
# @app.route('/get_data', methods=['GET'])
# def get_data():
#     with conn.cursor() as cur:
#         # Lấy dữ liệu từ database
#         cur.execute("SELECT status, userId FROM text_data LIMIT 1;")
#         text_data = cur.fetchone()

#         cur.execute("SELECT image_path FROM image_data LIMIT 1;")
#         image_data = cur.fetchone()

#         if not text_data or not image_data:
#             return jsonify({"error": "No data available"}), 404

#         # Lấy thông tin status, userId và đường dẫn ảnh
#         status = text_data[0]
#         userId = text_data[1]
#         image_path = image_data[0]

#         # Kiểm tra nếu file ảnh không tồn tại
#         if not os.path.exists(image_path):
#             return jsonify({"error": "Image file not found"}), 404

#         # Trả về dữ liệu dưới dạng form-data
#         def generate():
#             boundary = "----CustomBoundaryForMultipart"
#             yield f"--{boundary}\r\n"
#             yield f'Content-Disposition: form-data; name="status"\r\n\r\n{status}\r\n'
#             yield f"--{boundary}\r\n"
#             yield f'Content-Disposition: form-data; name="userId"\r\n\r\n{userId}\r\n'
#             yield f"--{boundary}\r\n"
#             yield f'Content-Disposition: form-data; name="image"; filename="{os.path.basename(image_path)}"\r\n'
#             yield "Content-Type: image/jpeg\r\n\r\n"
#             with open(image_path, "rb") as img_file:
#                 yield img_file.read()
#             yield f"\r\n--{boundary}--\r\n"

#         headers = {
#             "Content-Type": f"multipart/form-data; boundary=----CustomBoundaryForMultipart"
#         }
#         return Response(generate(), headers=headers)

# Endpoint get_data
@app.route('/get_data', methods=['GET'])
def get_data():
    with conn.cursor() as cur:
        # Lấy dữ liệu từ database
        cur.execute("SELECT status, userId FROM text_data LIMIT 1;")
        text_data = cur.fetchone()

        cur.execute("SELECT image_path FROM image_data LIMIT 1;")
        image_data = cur.fetchone()

        if not text_data or not image_data:
            return jsonify({"error": "No data available"}), 404

        # Lấy thông tin status, userId và đường dẫn ảnh
        status = text_data[0]
        userId = text_data[1]
        image_path = image_data[0]

        # Kiểm tra nếu file ảnh không tồn tại
        if not os.path.exists(image_path):
            return jsonify({"error": "Image file not found"}), 404

        # Đọc nội dung ảnh dưới dạng base64 để gửi trong JSON
        with open(image_path, "rb") as img_file:
            import base64
            image_base64 = base64.b64encode(img_file.read()).decode('utf-8')

        # Trả về dữ liệu dạng JSON
        return jsonify({
            "status": status,
            "userId": userId,
            "image": image_base64
        }), 200


# Endpoint check_data
@app.route('/check_data', methods=['POST'])
def check_data():
    try:
        data = request.get_json()
        if not data or data.get("status") != "success":
            return jsonify({"error": "Invalid request"}), 400

        # Xóa dữ liệu khi nhận "success"
        clear_data()
        return jsonify({"message": "Data cleared successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True)
