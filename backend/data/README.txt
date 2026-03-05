DATA DIRECTORY
==============

Place your GDPR articles JSONL file here before running setup_index.py.

Supported files (checked in this order)
---------------------------------------
  gdpr_articles.jsonl   (preferred)
  articles.jsonl        (fallback)

gdpr_articles.jsonl – expected keys per line:
  article_number  : e.g. "Article 1 Subject-matter and objectives"
  article_text    : full legal text of the article

articles.jsonl – alternative keys per line:
  input-text   : article title/number
  output-text  : full legal text

One JSON object per line (JSONL). Example line:
  {"article_number": "Article 1 Subject-matter and objectives", "article_text": "(1) This Regulation lays down rules..."}

This directory may contain index_state.json (gitignored). Do not commit large dataset files.
