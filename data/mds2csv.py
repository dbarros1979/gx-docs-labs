import requests
import csv

url = "https://api.github.com/repos/dbarros1979/gx-docs-labs/contents"
response = requests.get(url)
data = response.json()

with open('allsite.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Topic", "Line"])
    for item in data:
        if item["type"] == "file" and item["name"].endswith(".md"):
            url = item["url"]
            response = requests.get(url)
            content = response.json()["content"]
            decoded_content = base64.b64decode(content).decode("utf-8")
            lines = decoded_content.splitlines()
            for line in lines:
                if line.startswith("#"):
                    topic = line.strip("#").strip()
                else:
                    writer.writerow([topic, line])
