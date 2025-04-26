import json

# Output JSONL file
output_file = "combined_plans.jsonl"

# Process files from plan0.json to plan63.json
with open(output_file, 'w', encoding='utf-8') as outfile:
    for i in range(164):
        input_file = f"plan{i}.json"
        try:
            with open(input_file, 'r', encoding='utf-8') as infile:
                data = json.load(infile)
                # Write each JSON object as a line in the output file
                json.dump(data, outfile, ensure_ascii=False)
                outfile.write('\n')
        except FileNotFoundError:
            print(f"Warning: {input_file} not found, skipping...")
        except json.JSONDecodeError:
            print(f"Warning: {input_file} contains invalid JSON, skipping...")

print("Conversion completed. Check combined_plans.jsonl")