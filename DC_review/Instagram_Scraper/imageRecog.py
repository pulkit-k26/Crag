import os
import json
import time
from groq import Groq
import dotenv
import pandas as pd

# Load environment variables (FIXED API KEY REFERENCE)
dotenv.load_dotenv()
client = Groq(api_key=os.environ.get("Groq_API_key"))  # ✅ Correct variable name

# Paths
input_json_path = "instagram_off_data_DC.json"
output_csv_path = "instagram_off_data_DC_big.csv"

# Load the JSON data
with open(input_json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

results = []

for entry in data:
    caption = entry.get("caption", "")
    images = entry.get("images", [])
    
    if not images:
        print("No image found for entry, skipping.")
        continue
        
    # Get the base64 data URL from your JSON
    base64_data_url = images[0]  # Already contains "data:image/jpeg;base64,..."

    # Prepare prompt
    prompt = (
        "Generate a detailed, engaging description (about 100 words) for this Instagram photo. "
        "Describe the visual content, mood, and potential context. "
        f"Caption: {caption}\n"
        "Combine the visual analysis with the caption to create a single, cohesive description."
    )

    try:
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        # Use the base64 data URL directly
                        {"type": "image_url", "image_url": {"url": base64_data_url}}
                    ]
                }
            ],
            temperature=0.7,
            max_completion_tokens=300,
            top_p=1,
            stream=False,
            stop=None,
        )
        description = completion.choices[0].message.content
    except Exception as e:
        print("pk")
        description = f"Error generating description: {e}"

    results.append({
        "link": entry.get("link", ""),
        "posting_time": entry.get("posting_time",""),
        "likes": entry.get("likes",""),
        "hashtags": entry.get("hashtags",[]),
        "caption": caption,
        "description": description
    })
    print(f"Processed: {entry.get('link', '')}")
    time.sleep(0.5)  # Maintain rate limit protection

# Save results to CSV
df = pd.DataFrame(results)
df.to_csv(output_csv_path, index=False)
print(f"All descriptions saved to {output_csv_path}")