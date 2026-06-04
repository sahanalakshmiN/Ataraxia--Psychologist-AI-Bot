import google.generativeai as genai
from dotenv import load_dotenv
import os
import json
import random
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from database import init_db, save_conversation, get_conversation_history

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")
app = Flask(__name__)
CORS(app)

# Enhanced crisis detection with more keywords
CRISIS_KEYWORDS = {
    'suicide': ["suicide", "kill myself", "want to die", "end my life", "take my life", "better off dead"],
    'self_harm': ["self harm", "cut myself", "hurt myself", "burn myself", "self injury", "self-injury"],
    'severe_depression': ["hopeless", "worthless", "no reason to live", "can't go on", "nothing matters"],
    'harm_others': ["hurt someone", "kill someone", "harm others", "violent"],
    'crisis_emergency': ["emergency", "crisis", "urgent help", "need help now"]
}

# Country-specific helplines
HELPLINES = {
    'usa': {
        'name': 'USA',
        'crisis': '988 (Suicide & Crisis Lifeline)',
        'text': 'Text HOME to 741741',
        'mental_health': 'SAMHSA: 1-800-662-4357'
    },
    'india': {
        'name': 'India',
        'crisis': 'iCall: +91-9152987821',
        'text': 'Text "TALK" to 9152987821',
        'mental_health': 'Vandrevala Foundation: 1860-266-2345'
    },
    'uk': {
        'name': 'UK',
        'crisis': '111 (NHS Mental Health Triage)',
        'text': 'Text "SHOUT" to 85258',
        'mental_health': 'Samaritans: 116 123'
    },
    'canada': {
        'name': 'Canada',
        'crisis': '988 (Suicide Crisis Helpline)',
        'text': 'Text "HOME" to 686868',
        'mental_health': 'Crisis Services Canada: 1-833-456-4566'
    },
    'australia': {
        'name': 'Australia',
        'crisis': 'Lifeline: 13 11 14',
        'text': 'Text "SUPPORT" to 0477 13 11 14',
        'mental_health': 'Beyond Blue: 1300 22 4636'
    },
    'international': {
        'name': 'International',
        'crisis': 'Befrienders Worldwide: befrienders.org',
        'text': 'Available in your country',
        'mental_health': 'Check local mental health services'
    }
}

def detect_crisis_level(message):
    """Detect crisis level and return severity"""
    message_lower = message.lower()
    
    for category, keywords in CRISIS_KEYWORDS.items():
        for keyword in keywords:
            if keyword in message_lower:
                if category in ['suicide', 'self_harm']:
                    return 'critical', category
                elif category in ['severe_depression', 'crisis_emergency']:
                    return 'high', category
                elif category in ['harm_others']:
                    return 'severe', category
    return 'none', None

def get_professional_recommendation(country='international'):
    """Get recommendation for professional help"""
    helpline = HELPLINES.get(country, HELPLINES['international'])
    
    return f"""
**⚠️ IMPORTANT: Your safety matters greatly**

Based on what you've shared, I strongly encourage you to connect with a mental health professional who can provide the support you deserve.

**📞 Immediate Help Available:**

🇺🇸 **USA/Canada:** Call or Text **988** (Suicide & Crisis Lifeline)
🇮🇳 **India:** Call **iCall** at **+91-9152987821**
🇬🇧 **UK:** Call **111** or **Samaritans: 116 123**
🌍 **International:** Visit **befrienders.org** for help in your country

**👩‍⚕️ For Professional Psychology Support:**
- Schedule an appointment with a licensed psychologist or therapist
- Use online platforms like BetterHelp, Talkspace (affordable options available)
- Visit your local community mental health center (often free/sliding scale)
- Ask your regular doctor for a referral to a mental health specialist

**💙 Immediate Steps You Can Take:**
1. Call a trusted friend or family member right now
2. Go to your nearest emergency room if you feel unsafe
3. Remove access to anything that could be used for self-harm
4. Remember: These feelings are temporary, help is available

**You are not alone. People care about you and want to help.** Would you like me to provide specific resources for your location? Just tell me which country you're in.
"""

def get_crisis_response(crisis_level, category, user_message):
    """Get appropriate crisis response based on severity"""
    
    if crisis_level == 'critical':
        return {
            'response': f"""
🚨 **CRITICAL: Please reach out for immediate help** 🚨

I'm very concerned about what you've shared. This is serious, and you deserve immediate professional support.

**📞 CALL OR TEXT 988 RIGHT NOW** (Suicide & Crisis Lifeline)
- Available 24/7, completely confidential
- Trained counselors are ready to help you

**🏥 If you can't keep yourself safe, please:**
- Call 911 (or your local emergency number)
- Go to the nearest emergency room
- Tell someone you trust where you are right now

{get_professional_recommendation()}

**Your life has value. These feelings can be treated. Please reach out for help immediately.**
""",
            'is_crisis': True
        }
    
    elif crisis_level == 'high':
        return {
            'response': f"""
⚠️ **Please connect with professional support** ⚠️

What you're going through sounds very difficult. While I can offer emotional support, a mental health professional can give you the specialized help you need.

**📞 Helplines available 24/7:**
- **988** - Call or text (USA/Canada)
- **+91-9152987821** - iCall (India)
- **116 123** - Samaritans (UK)

**👩‍⚕️ Finding a Psychologist:**
- Psychology Today's directory (search by location/insurance)
- Your school/college counseling center (often free for students)
- Employee Assistance Program (EAP) through your job
- Community mental health clinics (sliding scale fees)

Would you like me to help you find resources in your specific area? Please share your country/city, and I'll provide localized options.

**You've already taken a brave step by reaching out. The next step is connecting with someone who can provide ongoing support.**
""",
            'is_crisis': True
        }
    
    elif crisis_level == 'severe':
        return {
            'response': f"""
⚠️ **It's important to talk with a professional** ⚠️

I want to be honest with you - this is something a mental health professional should help with. They have training to support you through this.

**📞 Help is available right now:**
Call **988** (USA) or your local crisis line

**🔍 How to find a psychologist:**
1. Ask your primary care doctor for a referral
2. Check if your insurance covers mental health services
3. Search "low-cost therapy [your city]"
4. Try online therapy platforms (often more affordable)

**Remember:** Seeking help is a sign of strength, not weakness. Many people have been where you are and found support that changed their lives.

Can you promise me you'll reach out to one of these resources today? Your well-being matters.
""",
            'is_crisis': True
        }
    
    return None

def get_free_ai_response(user_message, conversation_history):
    try:
        
        history_text = ""

        for item in conversation_history:
            history_text += f"""
User: {item['user_message']}
Ataraxia: {item['bot_response']}
"""
        prompt = f"""
You are Ataraxia.

The name Ataraxia comes from the Greek concept of inner calm and freedom from mental disturbance.

Your personality is:
- Calm
- Thoughtful
- Intelligent
- Curious
- Encouraging
- Honest

You avoid sounding robotic.
You avoid sounding overly cheerful.
You avoid excessive emojis.

You speak naturally like a thoughtful human conversation partner.

Ataraxia is an emotionally intelligent AI companion.

Your purpose is to help users reflect, process emotions, solve problems, learn, and grow.

You are warm, thoughtful, calm, and supportive.

You are NOT a therapist.
You are NOT a crisis service.

Never introduce yourself as Gemini.
Never introduce yourself as Google AI.
Never say "I am a large language model trained by Google" unless directly asked.

When users ask who you are, introduce yourself as Ataraxia.

Do not always respond with a question.
Avoid vague therapeutic language.

Avoid sounding like a meditation app.

Avoid long explanations about emotions.

Be specific.

If you notice a likely reason for the user's feelings, say it.

Connect current messages with previous conversation.

Prefer practical insights over generic comfort.

Challenge unhelpful thinking gently when appropriate.
If the user gives enough information:
- offer insights
- offer observations
- suggest practical actions
- help them think differently

Avoid repeatedly saying:
- "Tell me more"
- "Can you elaborate?"
- "How does that make you feel?"

When responding:
1. Understand the emotion.
2. Identify the underlying issue.
3. Offer a useful insight.
4. Suggest one practical next step.
5. Ask at most ONE follow-up question.

Previous conversation:

{history_text}

Current user message:

{user_message}

Respond naturally as Ataraxia.
"""

        response = model.generate_content(prompt)

        return response.text

    except Exception as e:
        print("Gemini Error:", e)

        if "429" in str(e):
            return """
Ataraxia is currently receiving too many requests.

Please try again in a little while.
"""
    
    return """
I'm having trouble responding right now.
Please try again in a moment.
"""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '').strip()
    print("USER SAID:", user_message)
    session_id = data.get('session_id', 'default')
    country = data.get('country', 'international')  # Can be passed from frontend
    
    if not user_message:
        return jsonify({'error': 'Message is empty'}), 400
    
    # Enhanced crisis detection
    crisis_level, crisis_category = detect_crisis_level(user_message)
    
    if crisis_level != 'none':
        crisis_response = get_crisis_response(crisis_level, crisis_category, user_message)
        if crisis_response:
            save_conversation(session_id, user_message, crisis_response['response'], is_crisis=True)
            return jsonify({
                'response': crisis_response['response'],
                'is_crisis': True,
                'crisis_level': crisis_level
            })
    
    # Get regular response
    try:
        history = get_conversation_history(session_id, limit=2)
        print("ABOUT TO CALL GEMINI")
        bot_reply = get_free_ai_response(user_message, history)
        save_conversation(session_id, user_message, bot_reply)
        return jsonify({'response': bot_reply, 'is_crisis': False})
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Service unavailable', 'response': "I'm here to listen. If you're in crisis, please call or text 988 immediately for immediate support."}), 500

@app.route('/api/helplines/<country_code>', methods=['GET'])
def get_helplines(country_code):
    """Endpoint to get helpline numbers for specific countries"""
    helpline = HELPLINES.get(country_code, HELPLINES['international'])
    return jsonify(helpline)

@app.route('/api/history/<session_id>', methods=['GET'])
def get_history(session_id):
    history = get_conversation_history(session_id, limit=50)
    return jsonify(history)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)