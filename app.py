from flask import Flask, request, jsonify, send_file, Response
import psycopg2
import os
import uuid
from flask_cors import CORS
import time
from threading import Lock

app = Flask(__name__)
CORS(app)

# Thư mục chứa ảnh
UPLOAD_FOLDER = 'statics'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Kết nối đến PostgreSQL
conn = psycopg2.connect(
    dbname="iotdb_f0sh",
    user="iotdb_f0sh_user",
    password="1CvEnRjDvzQwb745zituT9wudiUQRJT2",
    host="dpg-ctc4be8gph6c73abhgt0-a.singapore-postgres.render.com",
    port="5432"
)

# Tạo bảng nếu chưa tồn tại
def create_all_tables():
    with conn.cursor() as cur:
        # Wrap the table name 'user' in double quotes
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "user" (
                id SERIAL PRIMARY KEY,
                status TEXT NOT NULL,
                "userId" TEXT NOT NULL
            );
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS image (
                id SERIAL PRIMARY KEY,
                imagePath TEXT NOT NULL,
                "userId" INTEGER REFERENCES "user"(id) ON DELETE CASCADE
            );
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS status (
                id SERIAL PRIMARY KEY,
                imageStatus BOOLEAN DEFAULT TRUE,
                statusStatus BOOLEAN DEFAULT TRUE,
                userIdStatus BOOLEAN DEFAULT TRUE,
                "userId" INTEGER REFERENCES "user"(id) ON DELETE CASCADE,
                imageId INTEGER REFERENCES image(id) ON DELETE CASCADE
            );
        """)

        # Khởi tạo trạng thái nếu chưa tồn tại
        cur.execute("INSERT INTO status (id) VALUES (1) ON CONFLICT (id) DO NOTHING;")
        
        # Commit các thay đổi
        conn.commit()

create_all_tables()

# Xóa toàn bộ dữ liệu hiện tại
def clear_data():
    with conn.cursor() as cur:
        # Xóa dữ liệu trong database
        cur.execute("DELETE FROM \"user\";")
        cur.execute("DELETE FROM image;")
        # Xóa ảnh trong thư mục static
        for file in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        # Cập nhật trạng thái
        cur.execute("""
            UPDATE status 
            SET imageStatus = FALSE, statusStatus = FALSE, userIdStatus = FALSE
            WHERE id = 1;
        """)
        conn.commit()

recent_users = {}
lock = Lock()

@app.route('/send_data', methods=['POST'])
def send_data():
    # Lấy dữ liệu từ yêu cầu
    status = request.form.get('status')
    userId = request.form.get('userId')
    image = request.files.get('image')

    if not status or not userId or not image:
        return jsonify({"error": "Missing data"}), 400

    current_time = time.time()  # Thời gian hiện tại tính bằng giây

    with lock:
        # Kiểm tra xem (userId, status) có trong dictionary hay không
        user_status_key = (userId, status)
        if user_status_key in recent_users:
            last_time = recent_users[user_status_key]
            # Nếu trong vòng 15 giây, bỏ qua yêu cầu
            if current_time - last_time <= 15:
                return jsonify({"message": "Data already saved within the last 15 seconds for the same user and status"}), 200

        # Cập nhật thời gian xử lý gần nhất cho (userId, status)
        recent_users[user_status_key] = current_time

    # Xóa dữ liệu cũ trước khi lưu mới
    clear_data()

    # Lưu ảnh vào thư mục static
    image_name = f"{uuid.uuid4().hex}_{image.filename}"
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name)
    image.save(image_path)

    # Lưu dữ liệu mới vào database
    with conn.cursor() as cur:
        cur.execute("INSERT INTO \"user\" (status, \"userId\") VALUES (%s, %s) RETURNING id;", (status, userId))
        user_id = cur.fetchone()[0]
        
        cur.execute("INSERT INTO image (imagePath, \"userId\") VALUES (%s, %s) RETURNING id;", (image_path, user_id))
        image_id = cur.fetchone()[0]
        
        cur.execute("""
            UPDATE status 
            SET imageStatus = TRUE, statusStatus = TRUE, userIdStatus = TRUE, "userId" = %s, imageId = %s
            WHERE id = 1;
        """, (user_id, image_id))
        
        conn.commit()

    return jsonify({"message": "Data saved successfully"}), 200


# Endpoint get_data
@app.route('/get_data', methods=['GET'])
def get_data():
    with conn.cursor() as cur:
        # Lấy dữ liệu từ database
        cur.execute("SELECT status, \"userId\" FROM \"user\" LIMIT 1;")
        text_data = cur.fetchone()

        cur.execute("SELECT imagePath FROM image LIMIT 1;")
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
