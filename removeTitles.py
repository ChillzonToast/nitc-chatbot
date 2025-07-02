import json

with open('wiki_data.json', 'r') as f:
    data = json.load(f)

input_text = input("Enter the text to remove titles from: ")
new_data = {
    "pages": []
}
for page in data['pages']:
    if input_text not in page['title']:
        new_data['pages'].append(page)

with open('wiki_data.json', 'w') as f:
    json.dump(new_data, f, indent=2, ensure_ascii=False)
