from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_mail import Mail, Message
import jwt
import os
import random
import string
import boto3
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
from history import save_history
from analysis import int_anls
from match import match

app = Flask(__name__)
fallback_default_key="dkfjdfkdflkjnfjndfjndfjndfjnenfkljnfkjfnjfnedjndjndfjdnfjdnf"
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_default_key")   # Replace with a secure secret key

CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
dynamodb=boto3.resource('dynamodb',
    region_name=os.getenv('AWS_REGION', 'ap-south-1'))
table=dynamodb.Table("Youtube_Users")

# Mail Configuration
app.config["MAIL_SERVER"] = "smtp.gmail.com"  # Change for other providers
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
app.config["MAIL_USERNAME"] = "udaysrivastava0@gmail.com"
app.config["MAIL_PASSWORD"] = "vhwu sext smew vrah"
app.config["MAIL_DEFAULT_SENDER"] = "udaysrivastava0@gmail.com"
mail = Mail(app)
bcrypt = Bcrypt(app)

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))
# 📌 STEP 1: Send OTP to Frontend
@app.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get("email", "")
    subject = "OTP for signIn"
    print(email)
    if not email:
        return jsonify({"error": "Email is required"}), 400

    otp = generate_otp()
    message_body="Your OTP for Sign Up is "+str(otp)

    # In production, send OTP via email (e.g., SendGrid, SES)
    print(f"Generated OTP for {email}: {otp}")  # Debugging (REMOVE in production)
    msg = Message(subject, recipients=[email], body=message_body)
    try:
        mail.send(msg)
        return jsonify({"success": f"Email sent to {email}","otp":otp}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    # return jsonify({"otp": otp, "message": "OTP sent to your email"}), 200
@app.route('/savhistory',methods=['POST'])
def history():
    data=request.json
    response=save_history(table,data)
    return response

@app.route('/Int_analysis',methods=['POST'])
def Int_analysis():
    data=request.json
    response=int_anls(table,data)
    return response
@app.route('/matchmaker',methods=['POST'])
def matchmaker():
    data=request.json
    response=match(table,data)
    return response
# 📌 STEP 2: Store User After OTP is Verified in Frontend
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    email = data.get("email", "")
    password = data.get("password", "")  # Already hashed in frontend
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    # Store user in DynamoDB
    table.put_item(Item={"Email": email, "Password": password, "Verified": True})

    return jsonify({"message": "Signup successful!"}), 200


@app.route('/login', methods=['POST','GET'])
def login():
    # print(os.getenv('AWS_REGION', 'ap-south-1'))
    data = request.json  # Use JSON for POST requests
    # print(data)
    cred = data.get("cred", "")
    uid=data["email"]
    pas=data["password"]
    response = table.get_item(Key={"Email": uid})
    # print("Check it ",response)
    
    user = {
        "name": "Uday",
        "email": "udaysrivastava0@gmail.com",
        "image": "https://avatars.githubusercontent.com/u/19550456"
    }
    if "Item" not in response:
        return jsonify({"error": "User Not Found","userid":uid,"pass":pas}), 404
    if uid ==   response["Item"]["Email"] and bcrypt.check_password_hash(response["Item"]["Password"], pas):
    # if uid == "udaysrivastava0@gmail.com" and pas == "Uday4@":
        token = jwt.encode(
            {"user": uid, "exp": datetime.utcnow() + timedelta(hours=1)}, 
            SECRET_KEY, 
            algorithm="HS256"
        )
        user["name"]=uid.split("@")[0]
        user["email"]=uid
        return jsonify({"token": token, "data": user})
    print(f"Invalid Login Attempt: {uid}")
    return jsonify({"error": "Invalid credentials","userid":uid,"pass":pas}), 401

@app.route('/user-data', methods=['GET'])
def used_data():
    # Get the token from the Authorization header
    auth_header = request.headers.get('Authorization')

    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401  # Return 401 if no valid token

    token = auth_header.split(" ")[1]  # Extract token after "Bearer "

    # You should verify the token here (e.g., using JWT decoding)
    # Example (assuming JWT is used):
    # decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    
    # Sample user data
    user = {
        "name": "Uday",
        "email": "udaysrivastava0@gmail.com",
        "image": "https://avatars.githubusercontent.com/u/19550456"
    }

    return jsonify({"token": token, "data": user}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
