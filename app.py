from flask import Flask, request, jsonify, render_template
import pymongo
from datetime import datetime
import os
from dotenv import load_dotenv
import hashlib
import hmac

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

# MongoDB connection
MONGODB_URI = os.getenv('MONGODB_URI')
client = pymongo.MongoClient(MONGODB_URI)
db = client['webhook_db']
collection = db['github_events']

def format_timestamp(timestamp_str):
    """Convert ISO timestamp to readable format"""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%d %B %Y - %I:%M %p UTC')
    except:
        return timestamp_str

@app.route('/')
def index():
    """Main page displaying GitHub events"""
    return render_template('index.html')

@app.route('/api/events')
def get_events():
    """API endpoint to get latest events"""
    try:
        events = list(collection.find().sort('timestamp', -1).limit(50))
        for event in events:
            event['_id'] = str(event['_id'])
        return jsonify(events)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    """GitHub webhook endpoint"""
    try:
        payload = request.json
        headers = request.headers
        
        # Get event type from headers
        event_type = headers.get('X-GitHub-Event')
        
        if event_type == 'push':
            handle_push_event(payload)
        elif event_type == 'pull_request':
            handle_pull_request_event(payload)
        else:
            print(f"Unhandled event type: {event_type}")
        
        return jsonify({'status': 'success'}), 200
    
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return jsonify({'error': str(e)}), 500

def handle_push_event(payload):
    """Handle push events"""
    try:
        author = payload['pusher']['name']
        branch = payload['ref'].split('/')[-1]  # Extract branch from refs/heads/branch-name
        timestamp = payload['head_commit']['timestamp']
        
        event_data = {
            'action': 'push',
            'author': author,
            'to_branch': branch,
            'timestamp': timestamp,
            'formatted_message': f'"{author}" pushed to "{branch}" on {format_timestamp(timestamp)}',
            'created_at': datetime.utcnow()
        }
        
        collection.insert_one(event_data)
        print(f"Push event stored: {event_data['formatted_message']}")
        
    except Exception as e:
        print(f"Error handling push event: {str(e)}")

def handle_pull_request_event(payload):
    """Handle pull request events"""
    try:
        action = payload['action']
        
        if action == 'opened':
            author = payload['pull_request']['user']['login']
            from_branch = payload['pull_request']['head']['ref']
            to_branch = payload['pull_request']['base']['ref']
            timestamp = payload['pull_request']['created_at']
            
            event_data = {
                'action': 'pull_request',
                'author': author,
                'from_branch': from_branch,
                'to_branch': to_branch,
                'timestamp': timestamp,
                'formatted_message': f'"{author}" submitted a pull request from "{from_branch}" to "{to_branch}" on {format_timestamp(timestamp)}',
                'created_at': datetime.utcnow()
            }
            
            collection.insert_one(event_data)
            print(f"Pull request event stored: {event_data['formatted_message']}")
            
        elif action == 'closed' and payload['pull_request']['merged']:
            # Handle merge event
            author = payload['pull_request']['merged_by']['login']
            from_branch = payload['pull_request']['head']['ref']
            to_branch = payload['pull_request']['base']['ref']
            timestamp = payload['pull_request']['merged_at']
            
            event_data = {
                'action': 'merge',
                'author': author,
                'from_branch': from_branch,
                'to_branch': to_branch,
                'timestamp': timestamp,
                'formatted_message': f'"{author}" merged branch "{from_branch}" to "{to_branch}" on {format_timestamp(timestamp)}',
                'created_at': datetime.utcnow()
            }
            
            collection.insert_one(event_data)
            print(f"Merge event stored: {event_data['formatted_message']}")
            
    except Exception as e:
        print(f"Error handling pull request event: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)