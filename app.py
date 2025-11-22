import os
import uuid
import json
from flask import Flask, request, jsonify, render_template, redirect, url_for
from datetime import datetime, timedelta

app = Flask(__name__)
# IMPORTANT: In a real app, use a proper database (like Supabase, PostgreSQL, or Firestore).
# We are using a simple dictionary (in-memory) for the buildathon demo speed.
QUIZ_STORE = {} 

# --- UTILITY FUNCTIONS ---

def generate_unique_quiz_id():
    """Generates a short, unique ID for the quiz link."""
    # Use a part of a UUID for simplicity and uniqueness
    return str(uuid.uuid4())[:8] 

def get_base_url():
    """Determines the base URL for the generated link (IMPORTANT for deployment)."""
    # This should be replaced with your actual deployment URL (e.g., your_live-url.com)
    if os.environ.get('FLASK_ENV') == 'development':
        return "http://127.0.0.1:5000"
    # Placeholder for your deployed link (REPLACE THIS WHEN DEPLOYING!)
    return "https://gift-quiz-server.com" 

# --- API ENDPOINT FOR LOVABLE FRONT-END ---

@app.route('/api/create_quiz', methods=['POST'])
def create_quiz_data():
    """
    Receives quiz structure from the Lovable front-end and generates a unique link.
    
    Expected JSON body from Lovable:
    {
        "occasion": "Birthday",
        "questions": [
            {"id": "q1", "q": "What season reflects you the most?", "options": ["Summer", "Winter", ...]},
            ...
        ],
        "gifting_user_id": "user_123" // Optional: helps link the quiz back to the gifter
    }
    """
    try:
        data = request.get_json()
        if not data or 'questions' not in data:
            return jsonify({"error": "Invalid quiz data received"}), 400
        
        # 1. Generate unique ID
        quiz_id = generate_unique_quiz_id()
        
        # 2. Store quiz structure
        QUIZ_STORE[quiz_id] = {
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=30)).isoformat(), # 30-day policy
            "quiz_details": data,
            "answers": None, # Will be filled when the receiver submits the quiz
            "is_completed": False
        }
        
        # 3. Construct the shareable, working link
        quiz_url = f"{get_base_url()}/quiz/{quiz_id}"

        # 4. Return the unique link to the Lovable front-end
        return jsonify({
            "message": "Quiz created successfully",
            "quiz_id": quiz_id,
            "shareable_link": quiz_url
        }), 201

    except Exception as e:
        # In a production environment, log the full traceback.
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


# --- RECEIVER FACING ROUTES ---

@app.route('/quiz/<quiz_id>', methods=['GET'])
def start_quiz(quiz_id):
    """Renders the quiz page for the receiver based on the unique ID."""
    quiz_data = QUIZ_STORE.get(quiz_id)
    
    if not quiz_data:
        return render_template('not_found.html', message="Link not valid or has expired."), 404
    
    if datetime.fromisoformat(quiz_data['expires_at']) < datetime.now():
        return render_template('not_found.html', message="This quiz link has expired after 30 days."), 410

    if quiz_data['is_completed']:
        # If completed, redirect them to the thank you page with a message
        return redirect(url_for('quiz_completed_page', quiz_id=quiz_id, message="You have already completed this quiz. Thank you!"))

    # Render a simple HTML page displaying the questions dynamically
    return render_template(
        'quiz.html', 
        quiz_id=quiz_id, 
        questions=quiz_data['quiz_details']['questions']
    )

@app.route('/submit_quiz/<quiz_id>', methods=['POST'])
def submit_quiz(quiz_id):
    """Handles the receiver submitting their answers."""
    quiz_data = QUIZ_STORE.get(quiz_id)

    if not quiz_data:
        return jsonify({"error": "Quiz not found"}), 404

    # Collect answers from the form submission
    answers = request.form.to_dict()
    
    # Store the answers
    quiz_data['answers'] = answers
    quiz_data['is_completed'] = True
    
    # --- CRITICAL: AI ANALYSIS TRIGGER GOES HERE ---
    # After the buildathon, this is where you call your LLM/Fusion API 
    # using quiz_data['quiz_details'] and quiz_data['answers']
    # -------------------------------------------------

    # Redirect to the page that offers the share link
    return redirect(url_for('quiz_completed_page', quiz_id=quiz_id))

@app.route('/quiz_completed/<quiz_id>', methods=['GET'])
def quiz_completed_page(quiz_id):
    """Page shown after quiz completion, which displays the share option."""
    quiz_data = QUIZ_STORE.get(quiz_id)
    if not quiz_data:
        return render_template('not_found.html', message="Quiz data missing."), 404

    # The link to share the results (which points back to your Lovable app's API for results fetching)
    # The Lovable app will call the '/api/get_answers/<quiz_id>' route using this unique results link.
    results_link = f"{get_base_url()}/quiz_results/{quiz_id}"
    
    message = request.args.get('message', "Thanks for playing! Your answers are locked in.")

    # Render the thank_you page with the option to share
    return render_template('thank_you.html', message=message, results_link=results_link)

@app.route('/thank_you')
def thank_you_page():
    # Fallback route for generic thank you, but typically quiz_completed_page is used now.
    message="Thanks for playing! Your answers will help someone you know find the perfect surprise for you. You can now close this window."
    # Note: We need to pass results_link as None to avoid a template error if the receiver somehow lands here directly
    return render_template('thank_you.html', message=message, results_link=None)


@app.route('/get_answers/<quiz_id>', methods=['GET'])
def get_answers(quiz_id):
    """
    API endpoint for the Lovable front-end (gifter) to retrieve the answers 
    to trigger the final AI analysis with other data (screenshots).
    """
    quiz_data = QUIZ_STORE.get(quiz_id)
    if not quiz_data:
        return jsonify({"error": "Quiz not found or link expired"}), 404
    
    if not quiz_data['is_completed']:
        return jsonify({"message": "Quiz not yet completed."}), 202

    # Return the collected answers and original questions
    return jsonify({
        "quiz_id": quiz_id,
        "questions": quiz_data['quiz_details']['questions'],
        "answers": quiz_data['answers']
    })

# --- RUN THE APP ---

if __name__ == '__main__':
    
    # Add your actual questions generated in Lovable here:
    sample_quiz_data = {
        "occasion": "Just Because",
        "questions": [
            {"id": "q1", "q": "What season reflects you the most?", "options": ["Summer", "Autumn", "Winter", "Spring"]},
            {"id": "q2", "q": "Ideal day: Book & coffee OR Hiking trail?", "options": ["Book & coffee", "Hiking trail"]},
            {"id": "q3", "q": "If money wasn't an issue, what would you buy?", "options": ["Plane tickets", "A fancy watch", "Music equipment"]},
            {"id": "q4", "q": "What's your biggest pet peeve?", "options": ["Loud chewers", "Clutter", "Slow Wi-Fi", "Mornings"]},
            {"id": "q5", "q": "You prefer gifts that are...", "options": ["Practical/Useful", "Experiences", "Sentimental/Handmade", "High-Tech"]},
        ]
    }
    mock_id = generate_unique_quiz_id()
    QUIZ_STORE[mock_id] = {
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
        "quiz_details": sample_quiz_data,
        "answers": None,
        "is_completed": False
    }
    
    # Run in development mode
    app.run(debug=True)