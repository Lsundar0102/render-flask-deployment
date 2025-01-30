from dotenv import load_dotenv
import os
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

# Load environment variables
load_dotenv()

# Configure the Google Gemini API key
genai.configure(api_key="AIzaSyDl6CEtjqq2xyPnXbUvFLDgxPjWsoL6TB0")

app = Flask(__name__)
CORS(app)

# Static schema (mock schema example)
static_schema = {
    "stat_job": ["JobNumber", "Segment", "ExIm", "JobBranch", "JobCountry", "JobTag", "FN", "NBranch", "JobDate", "JobWeek", "JobMonth"]
}

# Default columns that should be included in the SQL query
DEFAULT_COLUMNS = [
    "JobNumber", "Segment", "ExIm", "JobBranch", "JobCountry",
    "JobTag", "FN", "NBranch", "JobDate", "JobWeek", "JobMonth"
]

# Function to generate a dynamic prompt for the AI
def generate_dynamic_prompt(schema):
    prompt = "You are an expert in converting English questions into SQL queries!\n\n"
    prompt += "The database contains the following tables and their respective columns:\n\n"
    for table, columns in schema.items():
        prompt += f"- **{table}**:\n"
        for column in columns:
            prompt += f"  - {column}\n"
    prompt += "\nRules for Generating SQL Queries:\n"
    prompt += "- Always include the following default columns in the SELECT clause, if they exist in the schema:\n"
    prompt += f"  {', '.join(DEFAULT_COLUMNS)}\n"
    prompt += "- If extra columns are requested, include them alongside the default columns.\n"
    prompt += "- If a vague or general question is asked, only include the default columns in the SELECT clause.\n"
    prompt += "- Ensure the query adheres to the given schema and uses valid syntax.\n"
    prompt += "- Respond with a valid SQL query or clarify why it cannot be created.\n"
    prompt += "- Focus on shipping-related queries. For example:\n"
    prompt +=   "  - For shipment details, use relevant tables and columns like 'shipment_id', 'status', 'origin', 'destination', etc.\n"
    return prompt

# Function to sanitize SQL query
def sanitize_sql_query(sql_query):
    sql_query = sql_query.replace("```", "").strip()
    sql_query = sql_query.replace("sql", "").strip()
    sql_query = sql_query.replace("\n", " ").replace("\r", " ")
    sql_query = " ".join(sql_query.split())

    return sql_query


def send_sql_to_external_api(sql_query):
    api_url = "https://vzone.in:6537/gpt-api/Jobs/GPT_StatJob_P"  # Your API URL
    params = {
        "UserID": "0"  # UserID as a query parameter
    }
    data = {
        "q": sql_query  # Send SQL query in the body
    }

    try:
        response = requests.post(api_url, params=params, json=data)  # Send data in JSON format and params in URL
        response.raise_for_status()  # Check if the request was successful
        print(f"API Response Status Code: {response.status_code}")  # Log status code

        return response.json()  # Return the response from the external API

    except requests.exceptions.RequestException as e:
            return {"error": f"Failed to send query to external API: {str(e)}"}


# Function to get a response from Google Gemini
def get_gemini_response(question, prompt):
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content([prompt, question])
    return response.text



@app.route("/get_query_result", methods=["GET"])
def get_query_result():
    # Get the question parameter from the request
    question = request.args.get("question")

    if not question:
        return jsonify({"error": "Question parameter is required"}), 400

    try:
        # Generate the dynamic prompt using the static schema
        dynamic_prompt = generate_dynamic_prompt(static_schema)

        # Generate the SQL query using the AI model (Gemini)
        ai_response = get_gemini_response(question, dynamic_prompt)
        sql_query = sanitize_sql_query(ai_response)
        print(sql_query)
        # Send the SQL query to the external API
        api_response = send_sql_to_external_api(sql_query)
        print(api_response)
         # Check if api_response is valid and serializable
        if isinstance(api_response, dict):
            return jsonify(api_response), 200  # Return the API response
        else:
            return jsonify({"error": "Failed to send query to external API"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
