from flask import Flask, request, jsonify
import os
import json

app = Flask(__name__)

FILE_PATH = 'result.json'

@app.route('/send_text', methods = ['POST'])
def send_text():
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    #Lưu dữ liệu vào file
    try:
        with open(FILE_PATH, 'w') as file:
            json.dump(data, file)
        return jsonify({'message': 'Text sent successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_text', methods = ['GET'])
def get_text():
    if not os.path.exists(FILE_PATH):
        return jsonify({'error': ''}), 404 
    try:
        with open(FILE_PATH, 'r') as file:
            data = json.load(file)
        return jsonify(data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/check_text', methods = ['POST'])
def checktext():  
    data = request.json
    if not data or data.get("status" != "success"):
        return jsonify({'error': "Invalid or missing 'status'"}), 400
    try:
        #xóa nội dung trong file
        with open(FILE_PATH, 'w') as file:
            file.truncate(0)
        return jsonify({'message': 'Text received successfully and deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)