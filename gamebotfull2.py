import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import joblib
import os

print("🔄 INITIALIZING BRAIN UPGRADE...")

# 1. Load Data
try:
    df = pd.read_csv('Gaming_dataset_new.csv')
    # CRITICAL FIX: Clean column names (remove hidden spaces)
    df.columns = df.columns.str.strip()
    print("✅ Dataset Loaded.")
except FileNotFoundError:
    print("❌ ERROR: 'Gaming_dataset_new.csv' not found.")
    exit()

# 2. Define the Target Logic (Risk Calculation)
# High Anxiety (>=7) AND High Gaming (>2 hours) = High Risk (1)
df['Target'] = df.apply(lambda row: 1 if (row['On a scale of 1 to 10, how anxious do you feel regularly?'] >= 7 or row['On a scale of 1 to 10, how stressed do you feel on average?'] >= 7) and row['How many hours do you play video games per day on average?'] > 2 else 0, axis=1)

# 3. select the 14 Exact Features (MUST match Chatbot inputs)
feature_columns = [
    'What is your age?', 
    'What is your gender?',
    'How many hours do you play video games per day on average?', 
    'How many days per week do you play games?',
    'What type of games do you mostly play?',
    'Do you often lose track of time while gaming?', 
    'Have you ever skipped meals or sleep due to gaming?',
    'Have others ever expressed concern about your gaming habits?',
    'On a scale of 1 to 10, how stressed do you feel on average?',
    'On a scale of 1 to 10, how anxious do you feel regularly?',
    'On average, how many hours of sleep do you get per night?',
    'How often do you feel socially withdrawn or isolated?',
    'Have you ever felt guilty or depressed after long gaming sessions?',
    'Do you think gaming helps you cope with stress or emotional issues?'
]

# Verify columns exist
missing_cols = [col for col in feature_columns if col not in df.columns]
if missing_cols:
    print(f"❌ ERROR: Missing columns in CSV: {missing_cols}")
    print("Check your CSV headers for typos.")
    exit()

X = df[feature_columns]
y = df['Target']

# 4. Smart Encoding (Text -> Numbers)
encoders = {}
for col in X.select_dtypes(include=['object']).columns:
    le = LabelEncoder()
    X[col] = le.fit_transform(X[col])
    encoders[col] = le

# 5. Train the Model
print("🧠 Training Neural Network on 14 Features...")
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X, y)

# 6. Force Save (Overwrite old files)
if os.path.exists('gaming_model_full.pkl'):
    os.remove('gaming_model_full.pkl')
if os.path.exists('encoders.pkl'):
    os.remove('encoders.pkl')

joblib.dump(model, 'gaming_model_full.pkl')
joblib.dump(encoders, 'encoders.pkl')

print("🎉 SUCCESS! New Brain (14 Features) saved.")
print(f"   Model expects: {model.n_features_in_} features.")
print("👉 NOW run 'streamlit run gamebotfull.py'")