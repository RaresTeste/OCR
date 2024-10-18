from flask import Flask, render_template, request
import requests

app = Flask(__name__)

# Afișează formularul principal pentru încărcare imagine
@app.route('/')
def index():
    return render_template('index.html')

# Ruta pentru gestionarea încărcării imaginii și trimiterea la API-ul OCR
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'image' not in request.files:
        return 'No file part', 400
    
    file = request.files['image']
    
    # Trimite imaginea la API-ul OCR
    files = {'image': file}
    response = requests.post('http://127.0.0.1:5000/upload', files=files)
    
    if response.status_code == 200:
        data = response.json()  # Datele returnate de API-ul OCR
        
        # Trimite datele extrase către result.html pentru a fi afișate în câmpuri
        return render_template('result.html', 
                               first_name=data['first_name'], 
                               second_name=data['second_name'], 
                               cnp=data['cnp'], 
                               nationality=data['nationality'], 
                               birthday_place=data['birthday_place'], 
                               adress=data['adress'])
    else:
        # Dacă OCR-ul nu a reușit, afișează un mesaj de eroare
        return 'Error processing the image', 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Aplicația frontend rulează pe portul 5001
