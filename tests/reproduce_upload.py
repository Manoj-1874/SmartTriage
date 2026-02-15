
import unittest
import io
import sys
import os
from unittest.mock import patch, MagicMock

# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

class TestMedicalUpload(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    @patch('flask_login.utils._get_user')
    def test_upload_csv(self, mock_current_user):
        import inspect
        func = self.app.application.view_functions['upload_medical_doc']
        print(f"Function Source File: {inspect.getfile(func)}")
        # print(f"Function Source: {inspect.getsource(func)}") # Too verbose, but file path helps

        # Mock current_user
        user = MagicMock()
        user.is_authenticated = True
        user.id = 1
        mock_current_user.return_value = user

        # CSV Content that mimics the issue
        # ID, Current Symptoms, Pre-existing Conditions
        csv_content = b"ID,Current Symptoms,Pre-existing Conditions\n6,mild fever and cough for 2 days,diabetes"
        
        data = {
            'file': (io.BytesIO(csv_content), 'patient_data.csv')
        }
        
        # We need to mock the user_loader to return a user user ID 1
        @app.login_manager.user_loader
        def load_user(user_id):
            u = MagicMock()
            u.id = user_id
            u.is_authenticated = True
            return u

        response = self.app.post('/api/upload-medical-doc', data=data, content_type='multipart/form-data')
        
        print(f"Status: {response.status_code}")
        print(f"Data: {response.data}")
        
        self.assertEqual(response.status_code, 200)
        # We expect this to FAIL (contain unwanted text) if our hypothesis is correct, 
        # or we check what it currently returns.
        # The issue is that parsed_data['symptoms'] contains the whole line.
        self.assertIn(b'extracted_text', response.data)
        import json
        json_data = json.loads(response.data)
        symptoms = json_data['parsed_data']['symptoms']
        
        with open('test_output.txt', 'w') as f:
            f.write(f"Parsed Symptoms: {symptoms}")
            
        print(f"Parsed Symptoms: {symptoms}")
        
        # Check case-insensitively
        # Now we expect "current symptoms" to NOT be in the value because we fixed the parsing
        self.assertNotIn("current symptoms", symptoms.lower())
        
        # Verify the actual value is correct
        self.assertIn("mild fever", symptoms.lower())
        self.assertIn("cough", symptoms.lower())

if __name__ == '__main__':
    unittest.main()
