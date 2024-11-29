from flask import Flask, request, jsonify
import os
import json
import time

app = Flask(__name__)

FILE_PATH = 'result.json'

# Global variables to store last received data and timestamp
last_data = None
last_timestamp = 0

@app.route('/send_text', methods=['POST'])
def send_text():
    global last_data, last_timestamp

    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Check if the received data is the same as the last one
    current_time = time.time()
    if data == last_data and (current_time - last_timestamp) < 15:
        # If the data is the same and it's within 15 seconds, save empty data
        data = {}
        with open(FILE_PATH, 'w') as file:
            json.dump(data, file)
        return jsonify({'message': 'Text is the same as previous, saved empty data'}), 200

    # Save the new data and update timestamp
    last_data = data
    last_timestamp = current_time

    try:
        with open(FILE_PATH, 'w') as file:
            json.dump(data, file)
        return jsonify({'message': 'Text sent successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_text', methods=['GET'])
def get_text():
    if not os.path.exists(FILE_PATH):
        return jsonify({'error': 'Không tìm thấy tệp'}), 404
    try:
        with open(FILE_PATH, 'r') as file:
            content = file.read()
            if not content.strip():  # Nếu tệp rỗng
                return jsonify({}), 200  # Trả về JSON rỗng
            data = json.loads(content)  # Phân tích cú pháp JSON
        return jsonify(data), 200
    except json.JSONDecodeError:
        return jsonify({'error': 'Định dạng JSON không hợp lệ'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/check_text', methods=['POST'])
def check_text():
    data = request.json
    if not data or data.get("status") != "success":
        return jsonify({'error': "Invalid or missing 'status'"}), 400
    try:
        # Xóa nội dung trong file
        with open(FILE_PATH, 'w') as file:
            file.truncate(0)
        return jsonify({'message': 'Text received successfully and deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
