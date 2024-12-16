from flask import Flask, request, render_template, jsonify
import sqlite3
import google.generativeai as genai

app = Flask(__name__)

# Configuration de l'API de IA Générative
genai.configure(api_key='YOUR_API_KEY')
model = genai.GenerativeModel('models/gemini-1.5-flash')

def extract_sql_query(text):
    # Supprimer les espaces blancs au début et à la fin
    text = text.strip()
    
    # Supprimer les backticks des blocs de code s'ils sont présents
    if text.startswith('```sql') and text.endswith('```'):
        text = text.strip('```').replace('sql\n', '').strip()
    
    return text

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def query():
    user_query = request.form.get('user_query')

    # Générer un prompt pour obtenir la requête SQL
    prompt = f"""
    Étant donné la demande de l'utilisateur : "{user_query}", générez une clause SQL pour filtrer la table products pour les articles et sélectionner ce que demande l'utilisateur.
    voici les colonnes disponibles : item_name, quantity, price, color

    Voici la liste de tous les articles disponibles dans le magasin : {get_available_items()}

    Répondez uniquement avec le code SQL si l'article est disponible dans le magasin. Par exemple, voici un code : SELECT DISTINCT item_name FROM products.
    Si la demande de l'utilisateur ne correspond à aucun article disponible dans le magasin, vous devez retourner No_result_found
    """

    response = model.generate_content(prompt)
    sql_query_response = response.text

    if "No_result_found" in sql_query_response:
        final_response = "Désolé, l'article que vous demandez n'est pas disponible dans notre magasin."
        return render_template('index.html', response=final_response)

    sql_query = extract_sql_query(sql_query_response)

    # Exécuter la requête SQL
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    try:
        cursor.execute(sql_query)
        result = cursor.fetchall()
        if not result:
            final_response = "Auc résultats trouvés pour votre requête."
        else:
            # Générer un prompt pour obtenir la réponse finale
            prompt = f"""
            Vous êtes un assistant de magasin, veuillez répondre à l'utilisateur sur la base des documents récupérés qui ont été récupérés de la base de données et qui contiennent les informations sur
            ce que l'utilisateur a demandé.
            Voici la demande originale de l'utilisateur : {user_query}
            et voici les documents récupérés de la base de données : {result}
            si le résultat n'est pas vide, c'est une confirmation que la demande de l'utilisateur est disponible
            """
            response = model.generate_content(prompt)

            final_response = response.text.strip()
    except Exception as e:
        final_response = f"Une erreur s'est produite : {str(e)}"
    finally:
        conn.close()

    return render_template('index.html', response=final_response)

# Fonction pour obtenir les articles disponibles dans la base de données
def get_available_items():
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT item_name FROM products")
    items = [row[0] for row in cursor.fetchall()]
    conn.close()
    return items

if __name__ == '__main__':
    app.run(debug=True)