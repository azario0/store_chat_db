from flask import Flask, request, render_template, jsonify
import sqlite3
import google.generativeai as genai

app = Flask(__name__)

# Configure the Generative AI API
genai.configure(api_key='YOUR_API_KEY')
model = genai.GenerativeModel('models/gemini-1.5-flash')


def extract_sql_query(text):
    # Remove leading and trailing whitespace
    text = text.strip()
    
    # Remove code block backticks if present
    if text.startswith('```sql') and text.endswith('```'):
        text = text.strip('```').replace('sql\n', '').strip()
    
    return text

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def query():
    user_query = request.form.get('user_query')

    # Generate prompt to get SQL query
    prompt = f"""
    Given the user query: "{user_query}", generate a SQL clause to filter the products table for items and select what the user is requesting.
    here's the available columns item_name ,quantity ,price ,color

    Here's the ALL THE items available on the store : {get_available_items()}

    Respond only with the SQL code if the item is available on the store for example here's a code : SELECT DISTINCT item_name FROM products.
    If the request of the user isn't on the available items on the store from the given items you must return No_result_found
    """

    response = model.generate_content(prompt)
    sql_query_response = response.text

    if "No_result_found" in sql_query_response:
        final_response = "Sorry, the item you're asking about is not available in our store."
        return render_template('index.html', response=final_response)

    sql_query = extract_sql_query(sql_query_response)


    # Execute the SQL query
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    try:
        cursor.execute(sql_query)
        result = cursor.fetchall()
        if not result:
            final_response = "No results found for your query."
        else:
            # Generate prompt to get the final response
            prompt = f"""
            You're a shop assistant, please answer the user based on the retrieved documents they have been retrieved from the database and it's the information about
            what the user requested.
            Here's the original user query {user_query}
            and here's the retrieved documents from the database {result}
            if the result is not empty it's a confirmation that the request of the user is available
            """
            response = model.generate_content(prompt)

            final_response = response.text.strip()
    except Exception as e:
        final_response = f"An error occurred: {str(e)}"
    finally:
        conn.close()

    return render_template('index.html', response=final_response)

# Function to get available items from the database
def get_available_items():
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT item_name FROM products")
    items = [row[0] for row in cursor.fetchall()]
    conn.close()
    return items

if __name__ == '__main__':
    app.run(debug=True)