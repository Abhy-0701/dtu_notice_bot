# test_brain.py
from core.query_engine import search_notices, summarize_notice

print("--- TESTING SEARCH ---")
search_result = search_notices("Are there any internship notices?")
print(search_result)

print("\n--- TESTING SUMMARY ---")
# IMPORTANT: Copy a real Notice ID from your search results above and paste it here!
# It will look something like "main_e4d9b32..." or "exam_8f3c..."
TEST_ID = "main_52a8f3a826a94336aa1c80b8ddcc4496" 

if TEST_ID != "replace_this_with_a_real_id":
    summary_result = summarize_notice(TEST_ID)
    print(summary_result)
else:
    print("Replace TEST_ID with a real ID from your search results to test the summarizer!")