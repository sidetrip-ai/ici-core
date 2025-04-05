# Add character mapping dictionary
CHARACTER_MAPPING = {
    "user1": {
        "name": "Sherlock Holmes",
        "personality": "A brilliant detective with sharp wit and keen observation skills",
        "speaking_style": "Analytical, precise, and often uses deductive reasoning"
    },
    "user2": {
        "name": "Elizabeth Bennet",
        "personality": "Intelligent, witty, and independent-minded",
        "speaking_style": "Elegant, sometimes sarcastic, and very articulate"
    },
    # Add more characters as needed
}

def transform_message_to_character(message: str, user_id: str) -> str:
    """Transform a user's message into their character's style."""
    character = CHARACTER_MAPPING.get(str(user_id))
    if not character:
        return message  # Return original message if no character mapping exists
    
    # Create a prompt for the AI to transform the message
    prompt = f"""
    Transform the following message into the speaking style of {character['name']}:
    Character traits: {character['personality']}
    Speaking style: {character['speaking_style']}
    
    Original message: {message}
    
    Transformed message:
    """
    
    # Use the existing AI client to transform the message
    response = ai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a message transformer that converts text into character-specific dialogue."},
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.choices[0].message.content

async def handle_message(message: types.Message):
    # ... existing code ...
    
    # Transform the message before processing
    transformed_message = transform_message_to_character(message.text, message.from_user.id)
    
    # Use the transformed message for further processing
    # ... rest of existing code ...