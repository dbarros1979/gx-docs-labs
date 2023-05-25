import os
import csv
import codecs

# Change directory to the parent directory
os.chdir('.')
dir = os.getcwd()

output_file = os.path.dirname(os.path.realpath(__file__)) + "\output.csv"
with codecs.open(output_file, "w", encoding="utf-8") as f:
    writer = csv.writer(f, quoting=csv.QUOTE_NONE, quotechar=None)
    writer.writerow(['prompt', 'raw_data'])

    row = []
    # r = root, d = directories, f = files
    for r, d, f in os.walk(dir):
        for file_name in f:
            if file_name.endswith('.md'):
                with codecs.open(os.path.join(r, file_name), "r", encoding="utf-8") as file:
                    #file_content = base64.b64decode(file.read()).decode("utf-8")
                    file_content = file.read()
                    if "#" in file_content:
                        prompt = ""
                        raw_data = ""
                        lines = file_content.splitlines()
                        for line in lines:
                            if "#" in line:
                                if len(prompt) > 0:
                                    row = [f'"{prompt.replace(",", "")}"', f'"{raw_data.replace(",", "")}"']
                                    writer.writerow(row)
                                    raw_data = ""
                                prompt = line.replace("#", "")
                            elif len(prompt) > 0:
                                raw_data += line
                        if len(prompt) > 0 and prompt not in row[0]:
                            row = [f'"{prompt.replace(",", "")}"', f'"{raw_data.replace(",", "")}"']
                            writer.writerow(row)