import csv
import os
from faker import Faker


fake = Faker()

SUBJECTS = [
    "Python",
    "Data Science",
    "Artificial Intelligence",
    "Machine Learning",
    "Database Management",
    "Web Development"
]


def generate_sample_candidates(total_records=20):
    os.makedirs("sample_data", exist_ok=True)

    file_path = "sample_data/sample_candidates.csv"

    with open(file_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow([
            "Candidate ID",
            "Name",
            "Email",
            "Age",
            "Exam Subject"
        ])

        for i in range(1, total_records + 1):
            writer.writerow([
                f"SC{i:03}",
                fake.name(),
                fake.unique.email(),
                fake.random_int(min=18, max=30),
                fake.random_element(elements=SUBJECTS)
            ])

    print(f"{total_records} sample candidate records generated successfully.")
    print(f"CSV file saved at: {file_path}")


if __name__ == "__main__":
    generate_sample_candidates()