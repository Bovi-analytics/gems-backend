from api.v1.views import app_views
from flask import jsonify, request
import requests
import json
import os



# Ideally, use environment variables in production!
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "https://adb-65044996157806.6.azuredatabricks.net")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN", "dapi8316292f686dc872297741ba02ed48d6-3")
DATABRICKS_ENDPOINT = f"https://adb-65044996157806.6.azuredatabricks.net/serving-endpoints/jds_rag_pinecone_plugin/invocations"
DATABRICKS_ENDPOINT_FULL = f"https://adb-65044996157806.6.azuredatabricks.net/serving-endpoints/jds_rag_pinecone_web/invocations"

@app_views.route("/gems/chat", methods=["POST"], strict_slashes=False)
def chat():
    try:
        user_message = request.json.get("message", "")
        if not user_message:
            return jsonify({"error": "No message provided"}), 400

        payload = json.dumps({
            "messages": [
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        })

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DATABRICKS_TOKEN}"
        }

        response = requests.post(DATABRICKS_ENDPOINT, headers=headers, data=payload)

        if response.status_code != 200:
            return jsonify({"error": f"Databricks returned status {response.status_code}", "details": response.text}), 500

        data = response.json()

        # Extract the AI response from the response structure
        ai_reply = ""
        if data and isinstance(data, list) and "messages" in data[0]:
            for msg in data[0]["messages"]:
                if msg.get("type") == "ai" and msg.get("content"):
                    ai_reply = msg.get("content", "")
                    break

        return jsonify({"response": ai_reply})

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500


@app_views.route("/gems/chat-full-page", methods=["POST"], strict_slashes=False)
def chat_full_page():
    try:
        user_message = request.json.get("message", "")
        if not user_message:
            return jsonify({"error": "No message provided"}), 400

        payload = json.dumps({
            "messages": [
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        })

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DATABRICKS_TOKEN}"
        }

        response = requests.post(DATABRICKS_ENDPOINT_FULL, headers=headers, data=payload)

        if response.status_code != 200:
            return jsonify({"error": f"Databricks returned status {response.status_code}", "details": response.text}), 500

        data = response.json()

        # Extract the AI response from the response structure
        ai_reply = ""
        if data and isinstance(data, list) and "messages" in data[0]:
            for msg in data[0]["messages"]:
                if msg.get("type") == "ai" and msg.get("content"):
                    ai_reply = msg.get("content", "")
                    break

        return jsonify({"response": ai_reply})

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500