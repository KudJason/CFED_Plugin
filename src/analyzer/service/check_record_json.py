import json

try:
    with open('src/analyzer/record.json', 'r') as f:
        data = json.load(f)
    
    # Print the top level keys
    print("Top level keys in record.json:")
    print(list(data.keys()))
    
    # If it's a list, print the length and first item's keys
    if isinstance(data, list):
        print(f"Length of records: {len(data)}")
        if len(data) > 0:
            print("Keys in first record:")
            print(list(data[0].keys()))
    
    print("Done.")
except Exception as e:
    print(f"Error reading record.json: {str(e)}") 