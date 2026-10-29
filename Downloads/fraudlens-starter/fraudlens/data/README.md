# Dataset
One JSON object per line in `samples.jsonl`:
`{"id": 1, "type": "text|screenshot|url|conversation", "content": "...", "label": "banking_kyc|upi_payment|phishing|fake_job|romance|legitimate", "collector": "member1"}`
Each member adds 15-20 samples (include legitimate ones). Screenshots go in `data/images/` and `content` is the filename.
The two lines in samples.jsonl are placeholders to show the format. Replace them with your real data.
