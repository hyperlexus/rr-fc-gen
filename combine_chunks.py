import glob
import os
import time
import re  # <-- Added this import


def combine_json_chunks():
    # sort chunk files
    chunk_files = sorted(
        glob.glob('data_chunk_*.json'),
        key=lambda f: int(re.search(r'\d+', f).group())
    )

    if not chunk_files:
        print("you fucked it. the files dont exist. make sure to run the other one first")
        return

    output_filename = 'final_data.json'
    print(f"combining {len(chunk_files)}...")
    start_time = time.time()

    with open(output_filename, 'w') as outfile:
        outfile.write('{')

        is_first_chunk = True
        for filename in chunk_files:
            with open(filename, 'r') as infile:
                content = infile.read()

                trimmed_content = content.strip()
                if trimmed_content.startswith('{') and trimmed_content.endswith('}'):
                    trimmed_content = trimmed_content[1:-1]

                if trimmed_content and not is_first_chunk:
                    outfile.write(',')

                outfile.write(trimmed_content)

                if trimmed_content:
                    is_first_chunk = False

        print("\ncombining...")
        outfile.write('}')

    end_time = time.time()
    file_size_gb = os.path.getsize(output_filename) / (1024 ** 3)

    print(f"\ncomplete. into {output_filename}, size {file_size_gb:.2f} GB, took {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    combine_json_chunks()
