from flask import Flask, render_template, request, jsonify
import json
import asyncio
from ici.adapters.orchestrators.telegram_orchestrator import TelegramOrchestrator

app = Flask(__name__)

# Predefined characters
CHARACTERS = {
    "1": {
        "name": "Sherlock Holmes",
        "personality": "A brilliant detective with sharp wit and keen observation skills",
        "speaking_style": "Analytical, precise, and often uses deductive reasoning"
    },
    "2": {
        "name": "Elizabeth Bennet",
        "personality": "Intelligent, witty, and independent-minded",
        "speaking_style": "Elegant, sometimes sarcastic, and very articulate"
    },
    "3": {
        "name": "Gandalf",
        "personality": "A wise and powerful wizard with deep knowledge",
        "speaking_style": "Mysterious, profound, and often speaks in riddles"
    }
}

@app.route('/')
def index():
    return render_template('index.html', characters=CHARACTERS)

@app.route('/generate', methods=['POST'])
async def generate_response():
    try:
        data = request.json
        character_id = data.get('character_id')
        message = data.get('message')
        
        if not character_id or not message:
            return jsonify({"error": "Missing character or message"}), 400
            
        character = CHARACTERS.get(character_id)
        if not character:
            return jsonify({"error": "Invalid character"}), 400
            
        # Initialize orchestrator
        orchestrator = TelegramOrchestrator()
        await orchestrator.initialize()
        
        # Create character-specific prompt
        character_prompt = f"""
        You are {character['name']}, {character['personality']}.
        Your speaking style is {character['speaking_style']}.
        
        User's question: {message}
        
        Please respond in character, maintaining your personality and speaking style.
        """
        
        # Process the query
        response = await orchestrator.process_query(
            source="web",
            user_id="web_user",
            query=character_prompt,
            additional_info=json.dumps({
                "session_id": "web-session",
                "character": character
            })
        )
        
        return jsonify({
            "response": response,
            "character_name": character['name']
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 