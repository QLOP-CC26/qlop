import kagglehub

# Download latest version
path = kagglehub.dataset_download("dataturks/resume-entities-for-ner")

print("Path to dataset files:", path)
