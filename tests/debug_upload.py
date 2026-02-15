
import io
import sys
import os
import inspect
from unittest.mock import MagicMock, patch

# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

def run_test():
    print("STARTING DEBUG SCRIPT", flush=True)
    
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()
    
    # Check source file
    func = app.view_functions['upload_medical_doc']
    print(f"Function Source File: {inspect.getfile(func)}", flush=True)

    with app.app_context():
        # Mock user
        with patch('flask_login.utils._get_user') as mock_current_user:
            user = MagicMock()
            user.is_authenticated = True
            user.id = 1
            mock_current_user.return_value = user
            
            # Use a session trick just in case
            with client.session_transaction() as sess:
                sess['_user_id'] = '1'

            @app.login_manager.user_loader
            def load_user(user_id):
                u = MagicMock()
                u.id = user_id
                u.is_authenticated = True
                return u

            # CSV Content
            csv_content = b"ID,Current Symptoms,Pre-existing Conditions\n6,mild fever and cough for 2 days,diabetes"
            data = {
                'file': (io.BytesIO(csv_content), 'patient_data.csv')
            }
            
            print("Sending POST request...", flush=True)
            response = client.post('/api/upload-medical-doc', data=data, content_type='multipart/form-data')
            
            print(f"Response Status: {response.status_code}", flush=True)
            print(f"Response Data: {response.data.decode('utf-8', errors='ignore')}", flush=True)

if __name__ == '__main__':
    run_test()
