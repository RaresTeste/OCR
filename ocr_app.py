#curl -X POST -F image=@/home/rares/OCR/WhatsApp\ Image\ 2024-09-19\ at\ 12.35.41\ PM.jpeg http://127.0.0.1:5000/upload
import psycopg2
import cv2
import numpy as np
import pytesseract
import re
from flask import Flask, request, jsonify

app = Flask("ocr_app")


@app.route('/')
def home():
    return "Welcome to the OCR API!"

pytesseract.pytesseract.tesseract_cmd = r"/usr/bin/tesseract"

# Preprocess the image to improve OCR accuracy
def preprocess_image(img):
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    alpha = 1.5
    beta = 50
    enhanced = cv2.convertScaleAbs(gray, alpha=alpha, beta=beta)
    blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)
    adaptive_threshold = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 41, 10)
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(adaptive_threshold, -1, kernel)
    resized_image = cv2.resize(sharpened, None, fx=1.4, fy=1.4, interpolation=cv2.INTER_LINEAR)
    return resized_image

# Funcțiile pentru extragerea datelor din imagine
def extract_cnp(text):
    id_match = re.search(r'\b\d{13}\b', text)
    return id_match.group(0) if id_match else "CNP not found"

def extract_name(text):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.search(r'Prenume|First name', line, re.IGNORECASE):
            if i + 1 < len(lines):
                possible_first_name = re.findall(r'\b[A-Z][a-zA-ZÀ-ÖØ-öø-ÿ-]+\b', lines[i + 1].strip())
                if possible_first_name:
                    return " ".join(possible_first_name).strip()
    return "First name not found"

def extract_second_name(text):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.search(r'Nume|Nom|Last name', line, re.IGNORECASE):
            if i + 1 < len(lines):
                possible_last_names = re.findall(r'\b[A-Z][a-zA-ZÀ-ÖØ-öø-ÿ-]+\b', lines[i + 1].strip())
                if possible_last_names:
                    return " ".join(possible_last_names).strip()
    return "Last name not found"

def extract_nationality(text):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.search(r'Cetățenie|Cetatenie|Nationalité|Nationality', line, re.IGNORECASE):
            if i + 1 < len(lines):
                nationality_match = re.findall(r'\b[A-Za-zÀ-ÖØ-öø-ÿ-]+\b', lines[i + 1].strip())
                if nationality_match:
                    return nationality_match[0].strip()
    return "Nationality not found"

def extract_birthday_place(text):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.search(r'Loc Nastere|Lieu de naissance|Place of birth', line, re.IGNORECASE):
            for j in range(1, 4):
                if i + j < len(lines):
                    possible_birthday_place = re.findall(r'[A-Za-z0-9.,\'\-À-ÖØ-öø-ÿ\s]+', lines[i + j].strip())
                    if possible_birthday_place:
                        birthday_place = " ".join(possible_birthday_place).strip()
                        birthday_place = re.sub(r'\s+', ' ', birthday_place)
                        return birthday_place if birthday_place else "Birthday Place not found"
    return "Birthday Place not found"

def extract_adress(text):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.search(r'Domiciliu|Adresse|Address', line, re.IGNORECASE):
            address_lines = []
            for j in range(1, 5):
                if i + j < len(lines):
                    next_line = lines[i + j].strip()
                    if len(next_line) > 5 and re.search(r'[A-Za-z0-9]', next_line):
                        address_lines.append(next_line)
            if address_lines:
                address = " ".join(address_lines)
                address = re.sub(r'\s+', ' ', address)
                return address.strip()
    return "Address not found"

# Endpoint pentru încărcarea imaginii și procesarea OCR
@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image file found!"}), 400

    file = request.files['image']
    img = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)
    
    if img is None:
        return jsonify({"error": "Invalid image!"}), 400

    processed_img = preprocess_image(img)
    text = pytesseract.image_to_string(processed_img)

    if not text.strip():
        return jsonify({"error": "No text extracted!"}), 400

    extracted_data = {
        "first_name": extract_name(text),
        "second_name": extract_second_name(text),
        "cnp": extract_cnp(text),
        "nationality": extract_nationality(text),
        "birthday_place": extract_birthday_place(text),
        "adress": extract_adress(text)
    }

    save_db(
        extracted_data["first_name"],
        extracted_data["second_name"],
        extracted_data["cnp"],
        extracted_data["birthday_place"],
        extracted_data["adress"]
    )

    return jsonify(extracted_data)

def save_db(first_name, second_name, cnp, birthday_place, adress):
    try:
        conn = psycopg2.connect(
            host="localhost",
            dbname="OCR",
            user="postgres",
            password="rares",
            port="5432"
        )
        cursor = conn.cursor()
        insert_query = """
            INSERT INTO Credentials (first_name, second_name, cnp, birthday_place, adress)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (first_name, second_name, cnp, birthday_place, adress))
        conn.commit()
    except Exception as e:
        print(f"A apărut o problemă cu conexiunea sau interogarea: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    app.run(debug=True)
